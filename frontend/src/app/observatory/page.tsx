"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function ObservatoryRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/dashboard");
  }, [router]);

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center text-slate-500 text-xs">
      <span>Redirecting to Dashboard...</span>
    </div>
  );
}
