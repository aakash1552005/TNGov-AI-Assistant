"use client";

import { useState, useRef, useEffect } from "react";

interface Citation {
  scheme_name: string;
  department: string;
  document_name: string;
  page_number: number;
  source_url: string;
  excerpt: string;
}

interface RetrievalMetadata {
  total_retrieved: number;
  top_rrf_score: number | null;
  vector_results_count: number;
  bm25_results_count: number;
  llm_called: boolean;
}

interface ChatResponse {
  answer: string;
  citations: Citation[];
  retrieval_metadata: RetrievalMetadata;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  metadata?: RetrievalMetadata;
  timestamp: string;
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const sampleQuestions = [
    {
      label: "Health Insurance",
      query:
        "What are the eligibility criteria for the Chief Minister's Comprehensive Health Insurance Scheme?",
    },
    {
      label: "மருத்துவக் காப்பீடு (Tamil)",
      query:
        "முதலமைச்சரின் விரிவான மருத்துவக் காப்பீட்டுத் திட்டத்தின் தகுதி என்ன?",
    },
    {
      label: "PMEGP Scheme",
      query:
        "What are the benefits under the Prime Minister's Employment Generation Programme (PMEGP)?",
    },
    {
      label: "Disability Allowance",
      query:
        "What is the unemployment allowance for differently abled persons in Tamil Nadu?",
    },
  ];

  const handleSend = async (queryText?: string) => {
    const textToSend = queryText || input;
    if (!textToSend.trim() || loading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: textToSend.trim(),
      timestamp: new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
    };

    setMessages((prev) => [...prev, userMessage]);
    if (!queryText) setInput("");
    setError(null);
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question: userMessage.content }),
      });

      if (!res.ok) {
        if (res.status === 422) {
          const errData = await res.json();
          throw new Error(
            errData.detail || "Invalid query format or length."
          );
        }
        throw new Error(
          `Server returned status ${res.status}. Please try again later.`
        );
      }

      const data: ChatResponse = await res.json();

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.answer,
        citations: data.citations,
        metadata: data.retrieval_metadata,
        timestamp: new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to fetch response.";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-screen max-h-screen bg-background text-foreground antialiased selection:bg-primary/30 selection:text-white">
      {/* ── Top Header ────────────────────────────────────────────── */}
      <header className="flex-none border-b border-border/60 bg-surface/80 backdrop-blur-xl px-6 py-4 z-20">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary via-primary-light to-accent flex items-center justify-center shadow-lg shadow-primary/20">
              <svg
                className="w-5 h-5 text-white"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={2}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.36 48.36 0 0 0 12 9.75c-2.551 0-5.056.2-7.5.582V21M3 21h18M12 6.75h.008v.008H12V6.75Z"
                />
              </svg>
            </div>
            <div>
              <h1 className="font-bold text-lg leading-snug tracking-tight">
                TN Gov <span className="text-accent">AI Scheme Assistant</span>
              </h1>
              <p className="text-xs text-muted">
                Official Tamil Nadu Welfare Scheme Information System
              </p>
            </div>
          </div>

          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-surface border border-border/80 text-xs">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-muted font-medium">Verified RAG Pipeline</span>
          </div>
        </div>
      </header>

      {/* ── Main Scrollable Container ─────────────────────────────── */}
      <main className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 scroll-smooth">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Welcome Screen when no messages */}
          {messages.length === 0 && (
            <div className="my-8 text-center space-y-6 animate-fade-in">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-surface border border-border shadow-xl">
                <svg
                  className="w-8 h-8 text-accent"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={1.5}
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a.75.75 0 0 1-1.007-.877c.303-1.127.359-2.316.143-3.486A8.784 8.784 0 0 1 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z"
                  />
                </svg>
              </div>

              <div className="space-y-2">
                <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">
                  How can I help you today?
                </h2>
                <p className="text-sm text-muted max-w-lg mx-auto leading-relaxed">
                  Ask questions in English or Tamil about eligibility, benefits,
                  and documentation for Tamil Nadu welfare schemes.
                </p>
              </div>

              {/* Sample Question Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-4 text-left max-w-2xl mx-auto">
                {sampleQuestions.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(q.query)}
                    className="p-4 rounded-xl bg-surface border border-border/80 hover:border-primary/50 hover:bg-surface-hover transition-all duration-200 text-xs space-y-1.5 group text-left shadow-sm"
                  >
                    <div className="font-semibold text-accent group-hover:text-primary-light transition-colors">
                      {q.label}
                    </div>
                    <div className="text-muted line-clamp-2 leading-snug">
                      "{q.query}"
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Messages Feed */}
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex flex-col ${
                msg.role === "user" ? "items-end" : "items-start"
              } space-y-2 animate-fade-in`}
            >
              <div className="flex items-center gap-2 px-1">
                <span className="text-[11px] font-medium text-muted">
                  {msg.role === "user" ? "You" : "TN Gov Assistant"}
                </span>
                <span className="text-[10px] text-muted/60">
                  {msg.timestamp}
                </span>
              </div>

              {/* Message Content Bubble */}
              <div
                className={`max-w-3xl rounded-2xl px-5 py-4 text-sm leading-relaxed shadow-sm ${
                  msg.role === "user"
                    ? "bg-gradient-to-r from-primary to-primary-light text-white rounded-br-none"
                    : "bg-surface border border-border/80 text-foreground rounded-bl-none"
                }`}
              >
                <div className="whitespace-pre-wrap">{msg.content}</div>

                {/* Metadata Badge for Assistant responses */}
                {msg.role === "assistant" && msg.metadata && (
                  <div className="mt-3 pt-2.5 border-t border-border/50 flex flex-wrap items-center gap-3 text-[11px] text-muted">
                    <span className="inline-flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-accent"></span>
                      Retrieved: {msg.metadata.total_retrieved} chunks
                    </span>
                    {msg.metadata.top_rrf_score && (
                      <span>
                        Top RRF: {msg.metadata.top_rrf_score.toFixed(4)}
                      </span>
                    )}
                    <span>
                      {msg.metadata.llm_called ? "LLM Generated" : "Direct Response"}
                    </span>
                  </div>
                )}
              </div>

              {/* Citations List for Assistant Messages */}
              {msg.role === "assistant" &&
                msg.citations &&
                msg.citations.length > 0 && (
                  <div className="mt-2 w-full max-w-3xl rounded-xl bg-surface/50 border border-border/60 p-4 space-y-3">
                    <div className="flex items-center justify-between text-xs font-semibold text-accent uppercase tracking-wider">
                      <span className="flex items-center gap-1.5">
                        <svg
                          className="w-3.5 h-3.5"
                          fill="none"
                          viewBox="0 0 24 24"
                          strokeWidth={2}
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25"
                          />
                        </svg>
                        Official Document Sources ({msg.citations.length})
                      </span>
                    </div>

                    <div className="grid grid-cols-1 gap-2.5">
                      {msg.citations.map((citation, cIdx) => (
                        <div
                          key={cIdx}
                          className="p-3 rounded-lg bg-surface/90 border border-border/80 text-xs space-y-1 hover:border-primary/40 transition-colors"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2 font-medium text-foreground">
                            <span className="text-primary-light font-semibold">
                              [{cIdx + 1}] {citation.scheme_name}
                            </span>
                            <span className="text-[11px] text-muted bg-background/60 px-2 py-0.5 rounded border border-border/40">
                              Page {citation.page_number}
                            </span>
                          </div>

                          <div className="text-muted/80 text-[11px] flex flex-wrap items-center gap-2">
                            <span>Department: {citation.department}</span>
                            <span>•</span>
                            <span className="truncate max-w-[200px]">
                              Doc: {citation.document_name}
                            </span>
                          </div>

                          {citation.source_url ? (
                            <div className="pt-1">
                              <a
                                href={citation.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-[11px] text-accent hover:underline font-medium"
                              >
                                View Official Portal
                                <svg
                                  className="w-3 h-3"
                                  fill="none"
                                  viewBox="0 0 24 24"
                                  strokeWidth={2}
                                  stroke="currentColor"
                                >
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"
                                  />
                                </svg>
                              </a>
                            </div>
                          ) : (
                            <div className="pt-0.5 text-[10px] text-muted/60 italic">
                              Official page link not available
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
            </div>
          ))}

          {/* Loading Indicator */}
          {loading && (
            <div className="flex flex-col items-start space-y-2 animate-pulse">
              <span className="text-[11px] font-medium text-muted px-1">
                TN Gov Assistant is thinking...
              </span>
              <div className="bg-surface border border-border/80 rounded-2xl rounded-bl-none px-5 py-4 flex items-center gap-2 text-sm text-muted">
                <div className="w-2 h-2 rounded-full bg-accent animate-bounce"></div>
                <div
                  className="w-2 h-2 rounded-full bg-accent animate-bounce"
                  style={{ animationDelay: "0.2s" }}
                ></div>
                <div
                  className="w-2 h-2 rounded-full bg-accent animate-bounce"
                  style={{ animationDelay: "0.4s" }}
                ></div>
                <span className="ml-2 text-xs">
                  Searching official documents & synthesizing answer...
                </span>
              </div>
            </div>
          )}

          {/* Error Banner */}
          {error && (
            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-xs flex items-center justify-between gap-3 shadow-lg">
              <div className="flex items-center gap-2">
                <svg
                  className="w-4 h-4 text-red-400 flex-shrink-0"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={2}
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z"
                  />
                </svg>
                <span>{error}</span>
              </div>
              <button
                onClick={() => setError(null)}
                className="text-red-400 hover:text-red-200 underline font-medium"
              >
                Dismiss
              </button>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* ── Input Box Footer ──────────────────────────────────────── */}
      <footer className="flex-none border-t border-border/60 bg-surface/80 backdrop-blur-xl p-4 z-20">
        <div className="max-w-4xl mx-auto space-y-3">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-end gap-3 bg-surface border border-border/80 rounded-2xl p-2 focus-within:border-primary/60 transition-colors shadow-lg"
          >
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question in English or Tamil (e.g. 'What are the eligibility criteria for CMCHIS?')"
              rows={1}
              className="flex-1 bg-transparent border-0 resize-none px-3 py-2 text-sm text-foreground focus:outline-none placeholder:text-muted/60 max-h-32 min-h-[40px]"
            />

            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="flex-none p-3 rounded-xl bg-gradient-to-r from-primary to-primary-light text-white font-medium hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-md shadow-primary/20"
            >
              {loading ? (
                <svg
                  className="w-5 h-5 animate-spin"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
              ) : (
                <svg
                  className="w-5 h-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={2}
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M6 12L3.269 3.126A59.768 59.768 0 0 1 21.485 12 59.77 59.77 0 0 1 3.27 20.876L5.999 12zm0 0h7.5"
                  />
                </svg>
              )}
            </button>
          </form>

          {/* Prominent Footer Disclaimer */}
          <p className="text-[11px] text-center text-muted/70">
            ⚠️ This is an AI assistant and not an official government source.
            Please verify all information with the concerned department before
            taking any action.
          </p>
        </div>
      </footer>
    </div>
  );
}
