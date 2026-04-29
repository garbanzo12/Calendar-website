export function getApiErrorMessage(error, fallbackMessage) {
  return (
    error?.userMessage ||
    error?.response?.data?.detail ||
    (typeof error?.response?.data === "string" ? error.response.data : "") ||
    error?.message ||
    fallbackMessage
  );
}
