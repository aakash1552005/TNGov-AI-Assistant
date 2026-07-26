export default function Home() {
  return (
    <main className="flex-1 flex flex-col items-center justify-center px-6 py-16">
      {/* Hero Section */}
      <div className="max-w-2xl mx-auto text-center space-y-8">
        {/* Logo / Icon */}
        <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-primary to-accent shadow-lg shadow-primary/20">
          <svg
            className="w-10 h-10 text-white"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.36 48.36 0 0 0 12 9.75c-2.551 0-5.056.2-7.5.582V21M3 21h18M12 6.75h.008v.008H12V6.75Z"
            />
          </svg>
        </div>

        {/* Title */}
        <div className="space-y-3">
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight">
            <span className="bg-gradient-to-r from-primary-light to-accent bg-clip-text text-transparent">
              TN Gov AI
            </span>{" "}
            <span className="text-foreground">Scheme Assistant</span>
          </h1>
          <p className="text-lg text-muted max-w-xl mx-auto leading-relaxed">
            Discover Tamil Nadu government welfare schemes through natural
            language questions. Every answer is grounded in official government
            documents with full source citations.
          </p>
        </div>

        {/* Status Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-surface border border-border text-sm">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-accent"></span>
          </span>
          <span className="text-muted">
            Milestone 1 Complete — Infrastructure Ready
          </span>
        </div>

        {/* Feature Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4">
          <div className="group p-5 rounded-xl bg-surface border border-border hover:border-primary/40 transition-all duration-300 hover:shadow-lg hover:shadow-primary/5">
            <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center mb-3 group-hover:bg-primary/20 transition-colors">
              <svg
                className="w-5 h-5 text-primary-light"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M10.5 21l5.25-11.25L21 21m-9-3h7.5M3 5.621a48.474 48.474 0 0 1 6-.371m0 0c1.12 0 2.233.038 3.334.114M9 5.25V3m3.334 2.364C11.176 10.658 7.69 15.08 3 17.502m9.334-12.138c.896.061 1.785.147 2.666.257m-4.589 8.495a18.023 18.023 0 0 1-3.827-5.802"
                />
              </svg>
            </div>
            <h3 className="font-semibold text-sm mb-1">Multilingual</h3>
            <p className="text-xs text-muted">English & Tamil support</p>
          </div>

          <div className="group p-5 rounded-xl bg-surface border border-border hover:border-primary/40 transition-all duration-300 hover:shadow-lg hover:shadow-primary/5">
            <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center mb-3 group-hover:bg-primary/20 transition-colors">
              <svg
                className="w-5 h-5 text-primary-light"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z"
                />
              </svg>
            </div>
            <h3 className="font-semibold text-sm mb-1">Source-Cited</h3>
            <p className="text-xs text-muted">Every answer traceable</p>
          </div>

          <div className="group p-5 rounded-xl bg-surface border border-border hover:border-primary/40 transition-all duration-300 hover:shadow-lg hover:shadow-primary/5">
            <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center mb-3 group-hover:bg-primary/20 transition-colors">
              <svg
                className="w-5 h-5 text-primary-light"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0-1 3m8.5-3 1 3m0 0 .5 1.5m-.5-1.5h-9.5m0 0-.5 1.5"
                />
              </svg>
            </div>
            <h3 className="font-semibold text-sm mb-1">RAG-Powered</h3>
            <p className="text-xs text-muted">Retrieval-augmented AI</p>
          </div>
        </div>

        {/* Disclaimer */}
        <p className="text-xs text-muted/60 max-w-md mx-auto pt-4 border-t border-border">
          ⚠️ This is an AI assistant, not an official government source. Please
          verify information with the concerned Tamil Nadu government department
          before acting.
        </p>
      </div>
    </main>
  );
}
