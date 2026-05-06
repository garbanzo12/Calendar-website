import { useState, useRef, useEffect } from "react";

import apiClient from "../api/client";
import { getApiErrorMessage } from "../api/errors";

export default function Chat({ onTaskCreated }) {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([
    {
      role: "system",
      content: "Try natural language: 'Lunch with Ana tomorrow at 1pm', 'Meeting next Monday at 3:30pm', 'Call mom on march 15 at 10am', 'Gym in 3 days at 7am'",
    },
  ]);
  const [isSending, setIsSending] = useState(false);
  const chatRef = useRef(null);

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSubmit = async (event) => {
    event.preventDefault();

    const trimmed = message.trim();
    if (!trimmed || isSending) {
      return;
    }

    const nextMessages = [...messages, { role: "user", content: trimmed }];
    setMessages(nextMessages);
    setMessage("");
    setIsSending(true);

    try {
      const response = await apiClient.post("/chat", { message: trimmed });
      const systemMessage = response.data.message || "Task scheduled successfully";

      setMessages([
        ...nextMessages,
        {
          role: "system",
          content: systemMessage,
        },
      ]);

      if (onTaskCreated) {
        onTaskCreated(response.data.task);
      }
    } catch (error) {
      const errorMessage = getApiErrorMessage(
        error,
        "I couldn't schedule that task. Please try another phrasing."
      );

      setMessages([
        ...nextMessages,
        {
          role: "system",
          content: errorMessage,
        },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <section className="panel chat-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Main feature</p>
          <h2>Chat scheduler</h2>
        </div>
      </div>

      <div className="chat-history" ref={chatRef}>
        {messages.map((entry, index) => (
          <article
            className={`message-bubble ${entry.role === "user" ? "user-message" : "system-message"}`}
            key={`${entry.role}-${index}`}
          >
            <span>{entry.role === "user" ? "You" : "Assistant"}</span>
            <p>{entry.content}</p>
          </article>
        ))}
      </div>

      <form className="chat-form" onSubmit={handleSubmit}>
        <textarea
          placeholder="Try: Lunch with Ana tomorrow at 1pm, Meeting next Monday at 3pm, Gym this Friday at 7am, Call mom on March 15 at 10am"
          rows="3"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
        />
        <button className="primary-button" disabled={isSending} type="submit">
          {isSending ? "Sending..." : "Send"}
        </button>
      </form>
    </section>
  );
}
