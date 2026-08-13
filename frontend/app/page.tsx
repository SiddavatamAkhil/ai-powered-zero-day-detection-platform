"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function RootPage() {
  const router = useRouter();

  useEffect(() => {
    const hasTokens = typeof window !== "undefined" && window.localStorage.getItem("zeroday_tokens");
    router.replace(hasTokens ? "/dashboard" : "/login");
  }, [router]);

  return null;
}
