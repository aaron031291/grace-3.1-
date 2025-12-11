import "./RAGTab.css";

export default function RAGTab() {
  return (
    <div className="rag-tab">
      <div className="tab-placeholder">
        <svg
          width="64"
          height="64"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        >
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="17 8 12 3 7 8"></polyline>
          <line x1="12" y1="3" x2="12" y2="15"></line>
        </svg>
        <h2>Document Upload & RAG</h2>
        <p>
          Upload documents to enhance your chatbot with Retrieval-Augmented
          Generation
        </p>
        <p className="coming-soon">Coming soon...</p>
      </div>
    </div>
  );
}
