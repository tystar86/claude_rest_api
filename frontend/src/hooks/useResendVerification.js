import { useCallback, useRef, useState } from "react";
import { resendVerification } from "../api/client";

export default function useResendVerification() {
  const [resendMessage, setResendMessage] = useState(null);
  const [resendIsError, setResendIsError] = useState(false);
  const [resending, setResending] = useState(false);
  const inflight = useRef(false);

  const handleResend = useCallback(async (email) => {
    if (inflight.current) return;
    inflight.current = true;
    setResending(true);
    setResendMessage(null);
    try {
      const result = await resendVerification(email);
      setResendMessage(result?.detail ?? "Verification email sent. Please check your inbox.");
      setResendIsError(false);
    } catch (err) {
      setResendMessage(err.response?.data?.detail ?? "Failed to resend verification email.");
      setResendIsError(true);
    } finally {
      setResending(false);
      inflight.current = false;
    }
  }, []);

  const clearResend = useCallback(() => {
    setResendMessage(null);
    setResendIsError(false);
  }, []);

  return { resendMessage, resendIsError, resending, handleResend, clearResend };
}
