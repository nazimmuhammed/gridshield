import React, { useState, useRef, useEffect } from "react";

/**
 * Dave - GridShield Alert Agent Chat Widget
 * ==========================================
 * Floating SCADA-styled blob (bottom-right). On click, Dave's robot head
 * pops up and perches on top edge of the chat panel. While Dave is
 * "thinking", an animated scanline/pulse effect plays instead of a
 * generic typing dots indicator - like a terminal actively processing.
 *
 * Drop this into frontend/src/components/DaveChat.jsx and render it
 * once anywhere in your App (e.g. <DaveChat /> near the root, it's
 * self-contained and fixed-positioned).
 *
 * Backend expected at POST http://localhost:8000/chat
 * Body: { session_id, message } -> { response, tools_used }
 */

const API_URL = "https://gridshield-backend.onrender.com/chat";
function getSessionId() {
  let id = sessionStorage.getItem("dave_session_id");
  if (!id) {
    id = "session-" + Math.random().toString(36).slice(2, 10);
    sessionStorage.setItem("dave_session_id", id);
  }
  return id;
}

// --- Dave the mascot: a rounded, friendly robot blob (Duolingo-style
// proportions - big head, big eyes, tiny body) instead of a flat panel.
function DaveHead({ thinking, open, bounce }) {
  return (
    <svg
      viewBox="0 0 140 150"
      width="86"
      height="92"
      style={{
        display: "block",
        filter: "drop-shadow(0 6px 14px rgba(56, 232, 199, 0.45))",
        animation: bounce ? "daveIdleBounce 2.4s ease-in-out infinite" : "none",
      }}
    >
      <defs>
        <linearGradient id="daveBody" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#2fd8b8" />
          <stop offset="100%" stopColor="#1f9e88" />
        </linearGradient>
        <radialGradient id="daveCheekGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#38e8c7" stopOpacity="0.9" />
          <stop offset="100%" stopColor="#38e8c7" stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* antenna */}
      <line x1="70" y1="6" x2="70" y2="24" stroke="#1c3d38" strokeWidth="4" strokeLinecap="round" />
      <circle cx="70" cy="6" r="6" fill="#ffd166">
        <animate attributeName="opacity" values="1;0.4;1" dur="1.8s" repeatCount="indefinite" />
      </circle>

      {/* little round ears/side bumps */}
      <circle cx="18" cy="72" r="12" fill="#1f9e88" />
      <circle cx="122" cy="72" r="12" fill="#1f9e88" />

      {/* main rounded body/head - one big friendly blob */}
      <ellipse cx="70" cy="82" rx="58" ry="54" fill="url(#daveBody)" />

      {/* belly/face panel */}
      <ellipse cx="70" cy="90" rx="42" ry="38" fill="#0d1a18" />

      {/* eyes */}
      <g>
        <circle cx="52" cy="86" r="13" fill="#ffffff" />
        <circle cx="88" cy="86" r="13" fill="#ffffff" />
        <circle cx="53" cy="88" r="6.5" fill="#0b1015">
          {thinking ? (
            <animate attributeName="cx" values="47;59;47" dur="1.4s" repeatCount="indefinite" />
          ) : (
            <animate attributeName="ry" values="6.5;0.5;6.5" dur="4s" begin="1s" repeatCount="indefinite" />
          )}
        </circle>
        <circle cx="89" cy="88" r="6.5" fill="#0b1015">
          {thinking ? (
            <animate attributeName="cx" values="83;95;83" dur="1.4s" repeatCount="indefinite" />
          ) : (
            <animate attributeName="ry" values="6.5;0.5;6.5" dur="4s" begin="1s" repeatCount="indefinite" />
          )}
        </circle>
      </g>

      {/* rosy cheek glows */}
      <circle cx="36" cy="102" r="9" fill="url(#daveCheekGlow)" />
      <circle cx="104" cy="102" r="9" fill="url(#daveCheekGlow)" />

      {/* smile */}
      <path
        d="M 56 108 Q 70 118 84 108"
        stroke="#38e8c7"
        strokeWidth="3.5"
        strokeLinecap="round"
        fill="none"
      />

      {/* tiny stubby arms */}
      <circle cx="14" cy="100" r="9" fill="#2fd8b8" />
      <circle cx="126" cy="100" r="9" fill="#2fd8b8" />
    </svg>
  );
}

// "Writing" indicator - a little notepad with a pencil that scribbles
// across it, like Dave is jotting down the answer by hand.
function WritingIndicator() {
  return (
    <div style={styles.writingRow}>
      <svg viewBox="0 0 90 46" width="78" height="40">
        {/* paper */}
        <rect x="4" y="4" width="82" height="38" rx="4" fill="#0d1a18" stroke="#26313d" strokeWidth="1.5" />
        {/* scribble lines that "write themselves" */}
        <path
          d="M14 16 H 56"
          stroke="#38e8c7"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeDasharray="42"
          strokeDashoffset="42"
        >
          <animate
            attributeName="stroke-dashoffset"
            values="42;42;0;0;42"
            keyTimes="0;0.02;0.28;0.9;1"
            dur="1.8s"
            repeatCount="indefinite"
          />
        </path>
        <path
          d="M14 25 H 46"
          stroke="#38e8c7"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeDasharray="32"
          strokeDashoffset="32"
        >
          <animate
            attributeName="stroke-dashoffset"
            values="32;32;0;0;32"
            keyTimes="0;0.35;0.6;0.9;1"
            dur="1.8s"
            repeatCount="indefinite"
          />
        </path>
        <path
          d="M14 34 H 64"
          stroke="#38e8c7"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeDasharray="50"
          strokeDashoffset="50"
        >
          <animate
            attributeName="stroke-dashoffset"
            values="50;50;50;0;0;50"
            keyTimes="0;0.65;0.68;0.9;0.95;1"
            dur="1.8s"
            repeatCount="indefinite"
          />
        </path>
        {/* pencil - moves back and forth like an actively writing hand */}
        <g>
          <animateTransform
            attributeName="transform"
            type="translate"
            values="14,12; 56,16; 14,25; 46,29; 14,34; 64,38; 14,12"
            keyTimes="0; 0.28; 0.35; 0.6; 0.68; 0.9; 1"
            dur="1.8s"
            repeatCount="indefinite"
          />
          <g transform="rotate(-40)">
            <rect x="0" y="-2.5" width="18" height="5" rx="2" fill="#ffd166" />
            <polygon points="18,-2.5 24,0 18,2.5" fill="#8a5a2b" />
            <rect x="-3" y="-2.5" width="4" height="5" rx="1.5" fill="#e85d5d" />
          </g>
        </g>
      </svg>
      <span style={styles.writingLabel}>DAVE IS WRITING…</span>
    </div>
  );
}

export default function DaveChat() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Dave online. Ask me about a line, run a simulation, or tell me to alert the on-call engineer.",
    },
  ]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const scrollRef = useRef(null);
  const sessionId = useRef(getSessionId());

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, thinking, open]);

  async function sendMessage() {
    const text = input.trim();
    if (!text || thinking) return;

    setMessages((m) => [...m, { role: "user", content: text }]);
    setInput("");
    setThinking(true);

    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId.current, message: text }),
      });
      const data = await res.json();

      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: data.response || "No response.",
          tools: data.tools_used || [],
        },
      ]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content:
            "Connection lost to grid control backend. Is the server running on :8000?",
        },
      ]);
    } finally {
      setThinking(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  return (
    <div style={styles.root}>
      {open && (
        <div style={styles.panel}>
          {/* Dave perches on the top edge of the panel */}
          <div style={styles.perch}>
            <DaveHead thinking={thinking} open={open} bounce={!thinking} />
          </div>

          <div style={styles.header}>
            <div>
              <div style={styles.headerTitle}>DAVE</div>
              <div style={styles.headerSub}>Grid Alert Agent · online</div>
            </div>
            <button style={styles.closeBtn} onClick={() => setOpen(false)}>
              ✕
            </button>
          </div>

          <div style={styles.messages} ref={scrollRef}>
            {messages.map((m, i) => (
              <div
                key={i}
                style={{
                  ...styles.bubbleRow,
                  justifyContent: m.role === "user" ? "flex-end" : "flex-start",
                }}
              >
                <div
                  style={{
                    ...styles.bubble,
                    ...(m.role === "user" ? styles.bubbleUser : styles.bubbleDave),
                  }}
                >
                  {m.content}
                  {m.tools && m.tools.length > 0 && (
                    <div style={styles.toolLog}>
                      {m.tools.map((t, j) => (
                        <div key={j} style={styles.toolLine}>
                          <span style={styles.toolDot} />
                          {t.tool}
                          {t.result?.status ? ` → ${t.result.status}` : ""}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {thinking && (
              <div style={{ ...styles.bubbleRow, justifyContent: "flex-start" }}>
                <div style={{ ...styles.bubble, ...styles.bubbleDave }}>
                  <WritingIndicator />
                </div>
              </div>
            )}
          </div>

          <div style={styles.inputRow}>
            <input
              style={styles.input}
              placeholder="Ask Dave about a line, e.g. 'what if line 27 fails?'"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <button style={styles.sendBtn} onClick={sendMessage} disabled={thinking}>
              ➤
            </button>
          </div>
        </div>
      )}

      {/* Floating blob trigger */}
      <button
        style={styles.blob}
        onClick={() => setOpen((o) => !o)}
        aria-label="Open Dave chat"
      >
        <div style={styles.blobPulse} />
        <DaveHead thinking={false} open={open} bounce={!open} />
      </button>

      <style>{keyframes}</style>
    </div>
  );
}

const keyframes = `
@keyframes daveIdleBounce {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  50% { transform: translateY(-6px) rotate(-2deg); }
}
@keyframes daveBarBounce {
  0%, 100% { transform: scaleY(0.3); opacity: 0.4; }
  50% { transform: scaleY(1); opacity: 1; }
}
@keyframes blobPulseRing {
  0% { transform: scale(0.9); opacity: 0.6; }
  100% { transform: scale(1.6); opacity: 0; }
}
`;

const COLORS = {
  bg: "#0b1015",
  panelBg: "#111820",
  border: "#26313d",
  accent: "#38e8c7",
  accentDim: "#1f5f56",
  text: "#dbe6ee",
  textDim: "#7f92a3",
  userBubble: "#1b3a52",
  daveBubble: "#161f28",
};

const styles = {
  root: {
    position: "fixed",
    bottom: "24px",
    right: "24px",
    zIndex: 9999,
    fontFamily:
      "'JetBrains Mono', 'Courier New', monospace, -apple-system, sans-serif",
  },
  blob: {
    position: "relative",
    width: "92px",
    height: "92px",
    borderRadius: "50%",
    background: `radial-gradient(circle at 30% 30%, #1e2933, ${COLORS.bg})`,
    border: `2px solid ${COLORS.accentDim}`,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: "pointer",
    boxShadow: `0 0 24px rgba(56,232,199,0.35), inset 0 0 12px rgba(0,0,0,0.6)`,
    overflow: "visible",
  },
  blobPulse: {
    position: "absolute",
    inset: 0,
    borderRadius: "50%",
    border: `2px solid ${COLORS.accent}`,
    animation: "blobPulseRing 2.2s ease-out infinite",
  },
  panel: {
    position: "absolute",
    bottom: "92px",
    right: "0",
    width: "360px",
    height: "480px",
    background: COLORS.panelBg,
    border: `1px solid ${COLORS.border}`,
    borderRadius: "14px",
    boxShadow: "0 12px 40px rgba(0,0,0,0.55)",
    display: "flex",
    flexDirection: "column",
    overflow: "visible",
  },
  perch: {
    position: "absolute",
    top: "-38px",
    left: "20px",
    zIndex: 2,
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "22px 16px 10px 100px",
    borderBottom: `1px solid ${COLORS.border}`,
  },
  headerTitle: {
    color: COLORS.accent,
    fontWeight: 700,
    fontSize: "15px",
    letterSpacing: "2px",
  },
  headerSub: {
    color: COLORS.textDim,
    fontSize: "11px",
    marginTop: "2px",
  },
  closeBtn: {
    background: "transparent",
    border: "none",
    color: COLORS.textDim,
    fontSize: "16px",
    cursor: "pointer",
  },
  messages: {
    flex: 1,
    overflowY: "auto",
    padding: "14px",
    display: "flex",
    flexDirection: "column",
    gap: "10px",
  },
  bubbleRow: {
    display: "flex",
  },
  bubble: {
    maxWidth: "82%",
    padding: "9px 12px",
    borderRadius: "10px",
    fontSize: "13px",
    lineHeight: 1.45,
    color: COLORS.text,
  },
  bubbleUser: {
    background: COLORS.userBubble,
    borderBottomRightRadius: "2px",
  },
  bubbleDave: {
    background: COLORS.daveBubble,
    border: `1px solid ${COLORS.border}`,
    borderBottomLeftRadius: "2px",
  },
  toolLog: {
    marginTop: "8px",
    paddingTop: "8px",
    borderTop: `1px dashed ${COLORS.border}`,
    fontSize: "10.5px",
    color: COLORS.textDim,
  },
  toolLine: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
    marginTop: "3px",
  },
  toolDot: {
    width: "5px",
    height: "5px",
    borderRadius: "50%",
    background: COLORS.accent,
    display: "inline-block",
  },
  writingRow: {
    display: "flex",
    flexDirection: "column",
    gap: "6px",
  },
  writingBars: {
    display: "flex",
    alignItems: "flex-end",
    gap: "3px",
    height: "14px",
  },
  writingBar: {
    width: "3px",
    height: "100%",
    background: COLORS.accent,
    borderRadius: "2px",
    animation: "daveBarBounce 0.9s ease-in-out infinite",
  },
  writingLabel: {
    fontSize: "9.5px",
    color: COLORS.textDim,
    letterSpacing: "1px",
  },
  inputRow: {
    display: "flex",
    gap: "8px",
    padding: "12px",
    borderTop: `1px solid ${COLORS.border}`,
  },
  input: {
    flex: 1,
    background: "#0d1319",
    border: `1px solid ${COLORS.border}`,
    borderRadius: "8px",
    padding: "9px 10px",
    color: COLORS.text,
    fontSize: "12.5px",
    outline: "none",
  },
  sendBtn: {
    background: COLORS.accentDim,
    border: "none",
    borderRadius: "8px",
    color: COLORS.accent,
    width: "38px",
    fontSize: "14px",
    cursor: "pointer",
  },
};