"""
Live packet simulation — closes another real gap from objective #11
("Live Packet Simulation"), which previously had no implementation at all.

Streams synthetically generated flow records through a trained model in
real time over a WebSocket, mimicking a live IDS feed for demo/dashboard
purposes. Deliberately synthetic rather than a real packet capture (no
raw socket / pcap access in this deployment, and capturing real traffic
without a lot more scoping around consent/legality is out of scope for a
capstone platform) — but the detection logic (load model, run inference,
apply OpenMax) is the real trained model, not mocked.
"""
import asyncio
import json
import os
import random
import sys
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/simulation", tags=["Live Simulation"])

ML_PACKAGE_PARENT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if ML_PACKAGE_PARENT not in sys.path:
    sys.path.insert(0, ML_PACKAGE_PARENT)


def _generate_synthetic_flow(num_features: int) -> list[float]:
    """
    A single synthetic flow-feature vector. Occasionally (10% of the time)
    generates an out-of-distribution vector (large values) to simulate a
    zero-day-style attack the model should flag as unknown — this is what
    lets the live feed visibly demonstrate open-set rejection, not just
    closed-set classification.
    """
    if random.random() < 0.1:
        return [random.gauss(50, 10) for _ in range(num_features)]  # OOD burst
    return [random.gauss(0, 1) for _ in range(num_features)]


@router.websocket("/ws/{model_id}")
async def live_simulation_feed(websocket: WebSocket, model_id: uuid.UUID):
    """
    Streams one simulated detection event per second. Each message:
        {"timestamp": ..., "predicted_class": ..., "confidence": ...,
         "is_unknown": bool}

    Auth note: WebSocket connections can't carry a standard Authorization
    header from a browser EventSource-style client easily, so this accepts
    a `token` query param instead (?token=<access_token>) — validated the
    same way as the HTTP JWT dependency. Documented here rather than
    silently left open, since it's a real deviation from the header-based
    auth used everywhere else in the API.
    """
    query_params = dict(websocket.query_params)
    token = query_params.get("token")

    from app.core.security import decode_token
    payload = decode_token(token) if token else None
    if not payload or payload.get("type") != "access":
        await websocket.close(code=4401, reason="Unauthorized")
        return

    await websocket.accept()

    try:
        import numpy as np
        import torch

        from app.core.config import settings
        from app.db.session import AsyncSessionLocal
        from app.repositories.ml_model_repository import SqlAlchemyMLModelRepository
        from ml.openmax.openmax import OpenMaxRecalibrator
        from ml.training.trainer import build_model

        async with AsyncSessionLocal() as session:
            repo = SqlAlchemyMLModelRepository(session)
            ml_model = await repo.get_model_by_id(model_id)

        if ml_model is None or ml_model.num_classes is None:
            await websocket.send_json({"error": "Model not found or not a supervised classifier."})
            await websocket.close()
            return

        torch_model = build_model(ml_model.architecture.value, ml_model.num_features, ml_model.num_classes)
        torch_model.load_state_dict(torch.load(ml_model.artifact_path, map_location="cpu"))
        torch_model.eval()

        openmax = None
        if ml_model.openmax_path and os.path.exists(ml_model.openmax_path):
            openmax = OpenMaxRecalibrator.load(ml_model.openmax_path)

        class_names = ml_model.class_names or [f"class_{i}" for i in range(ml_model.num_classes)]

        while True:
            flow = _generate_synthetic_flow(ml_model.num_features)
            x = torch.tensor([flow], dtype=torch.float32)
            with torch.no_grad():
                logits, embedding = torch_model(x, return_embedding=True)
                probs = torch.softmax(logits, dim=1).numpy()[0]

            predicted_idx = int(probs.argmax())
            is_unknown = False
            if openmax is not None:
                _, is_unknown = openmax.recalibrate(embedding[0].numpy(), logits[0].numpy())

            await websocket.send_json({
                "timestamp": asyncio.get_event_loop().time(),
                "predicted_class": class_names[predicted_idx] if not is_unknown else "unknown",
                "confidence": float(probs[predicted_idx]),
                "is_unknown": is_unknown,
            })
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001 - report the error to the client before closing
        try:
            await websocket.send_json({"error": str(exc)})
        except Exception:
            pass
