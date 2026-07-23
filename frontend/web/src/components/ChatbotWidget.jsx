import { useEffect, useRef, useState } from "react";
import { sendChatbotMessage } from "../services/ChatbotApi";
import "./ChatbotWidget.css";

function generateMessageId(suffix) {
  return `${Date.now()}-${suffix}`;
}

function ChatbotWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [error, setError] = useState("");

  const [messages, setMessages] = useState([
    {
      id: "greeting",
      role: "assistant",
      text: "Hello! How can I help you navigate your healthcare options today?",
    },
  ]);

  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isOpen]);

  async function handleSend(overrideText) {
    const text = (overrideText ?? inputValue).trim();

    if (!text || isSending) {
      return;
    }

    const userMessageId = generateMessageId("user");

    setMessages((prev) => [
      ...prev,
      { id: userMessageId, role: "user", text },
    ]);
    setInputValue("");
    setIsSending(true);
    setError("");

    try {
      const response = await sendChatbotMessage({ message: text });

      setMessages((prev) => [
        ...prev,
        {
          id: generateMessageId("assistant"),
          role: "assistant",
          text: response.message,
          fallbackUsed: response.fallback_used,
          suggestedPrompts: response.suggested_prompts,
        },
      ]);
    } catch (sendError) {
      setError(sendError.message || "Could not reach the assistant.");
    } finally {
      setIsSending(false);
    }
  }

  function handleKeyDown(event) {
    if (event.key === "Enter") {
      void handleSend();
    }
  }

  if (!isOpen) {
    return (
      <button
        type="button"
        className="chatbot-fab"
        onClick={() => setIsOpen(true)}
        aria-label="Open ClearPath AI Assistant"
      >
        <span role="img" aria-hidden="true">
          🤖
        </span>
      </button>
    );
  }

  return (
    <section
      className="chatbot-panel"
      role="dialog"
      aria-label="ClearPath AI Assistant"
    >
      <header className="chatbot-panel-header">
        <div className="chatbot-panel-title">
          <span role="img" aria-hidden="true">
            🤖
          </span>
          <span>ClearPath AI Assistant</span>
        </div>

        <button
          type="button"
          className="chatbot-close-button"
          onClick={() => setIsOpen(false)}
          aria-label="Close assistant"
        >
          ×
        </button>
      </header>

      <div className="chatbot-messages" ref={scrollRef}>
        {messages.map((msg) => (
          <div key={msg.id} className={`chatbot-message ${msg.role}`}>
            {msg.role === "assistant" && (
              <span className="chatbot-avatar" aria-hidden="true">
                ●
              </span>
            )}

            <div className="chatbot-bubble">
              <p>{msg.text}</p>

              {msg.fallbackUsed && (
                <span className="chatbot-fallback-note">
                  Answered using a general fallback response
                </span>
              )}

              {msg.suggestedPrompts && msg.suggestedPrompts.length > 0 && (
                <div className="chatbot-suggested-prompts">
                  {msg.suggestedPrompts.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      onClick={() => void handleSend(prompt)}
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {isSending && (
          <div className="chatbot-message assistant">
            <span className="chatbot-avatar" aria-hidden="true">
              ●
            </span>
            <div className="chatbot-bubble chatbot-typing">Typing…</div>
          </div>
        )}
      </div>

      {error && <p className="chatbot-error">{error}</p>}

      <div className="chatbot-input-row">
        <input
          type="text"
          value={inputValue}
          onChange={(event) => setInputValue(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about clinics, wait times, or access"
          disabled={isSending}
        />

        <button
          type="button"
          onClick={() => void handleSend()}
          disabled={isSending || !inputValue.trim()}
          aria-label="Send message"
        >
          ➤
        </button>
      </div>
    </section>
  );
}

export default ChatbotWidget;