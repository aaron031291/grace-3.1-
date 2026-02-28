/**
 * TabGuide — "What is this?" button for each tab.
 * Shows plain-English explanation of what the tab does.
 */
import { useState } from 'react';

const GUIDES = {
  chat: {
    title: "Chat — Talk to Grace",
    description: "This is where you talk to Grace about anything. She sees the whole system from a bird's eye view. Ask her questions, give her instructions, or just have a conversation. Toggle different AI models (Opus, Kimi, Qwen) for different perspectives.",
    tips: ["Try asking 'What's the health of the system?'", "Toggle multiple models for a roundtable discussion", "Use the World Model button to see system overview"],
  },
  folders: {
    title: "Folders — Your File System",
    description: "Create, organise, upload, and manage all your files and folders. Grace's Librarian automatically organises files into the right categories. You can upload files up to 5GB. Everything is tracked with Genesis Keys.",
    tips: ["Upload files by clicking the upload button", "Create nested folders for organisation", "The Librarian will suggest where files should go"],
  },
  docs: {
    title: "Docs — Your Document Library",
    description: "Every document uploaded anywhere in the system appears here. View them all in a list, or organised by folder. Search, filter, and manage your entire document collection.",
    tips: ["Switch between 'All Docs' and 'By Folder' views", "Upload directly here or through Folders tab", "Documents are automatically indexed for search"],
  },
  governance: {
    title: "Governance — Rules & Compliance",
    description: "Upload rules, laws, and policies that Grace must follow. GDPR, coding standards, company policies — whatever you upload becomes law for Grace. She'll follow these rules in every action she takes.",
    tips: ["Upload PDF/text files with your rules", "Set a persona for how Grace communicates", "Rules are enforced across ALL AI calls automatically"],
  },
  whitelist: {
    title: "Whitelist — Data Sources",
    description: "Add API endpoints and websites that Grace should learn from. She'll pull data, analyse it, and store the knowledge. The Flash Cache tab shows everything she's cached for fast lookup.",
    tips: ["Paste an API URL and Grace auto-connects", "Add YouTube channels, blogs, or websites to learn from", "Check Flash Cache for cached reference lookups"],
  },
  oracle: {
    title: "Oracle — Training & Knowledge",
    description: "The Oracle is where all of Grace's training data lives. See what she's learned, audit the quality, fill knowledge gaps. This is Grace's long-term knowledge base.",
    tips: ["Run an audit to find knowledge gaps", "Fill gaps by asking Kimi to research topics", "Check trust scores on training data quality"],
  },
  codebase: {
    title: "Codebase — Code Projects",
    description: "Create and manage code projects. Grace's coding agent generates code using 28 intelligence sources. Upload rules for the coding agent to follow. View and edit generated code.",
    tips: ["Create a project and describe what you want to build", "Upload coding rules the agent must follow", "Generated code goes through verification before you see it"],
  },
  tasks: {
    title: "Tasks — Activity & Planning",
    description: "See what Grace is doing right now (Live), submit new tasks, schedule future work, or use the Blueprint IDE to plan with Grace side-by-side. Grace plans while you think.",
    tips: ["Use Blueprint IDE for dual-pane planning", "Submit tasks for Grace to work on autonomously", "Schedule recurring tasks"],
  },
  apis: {
    title: "APIs — System Endpoints",
    description: "Browse every API endpoint in Grace's system. Run health checks, test endpoints, see diagnostics. This is the technical control panel.",
    tips: ["Run health checks to verify all systems", "Test any endpoint directly from this tab", "See which endpoints are most used"],
  },
  bi: {
    title: "BI — Business Intelligence",
    description: "Analytics and metrics about Grace's performance. LLM usage, document stats, activity trends, memory statistics. See how Grace is performing over time.",
    tips: ["Check LLM usage to track API costs", "View memory stats across all systems", "See activity trends over the last 7 days"],
  },
  health: {
    title: "Health — System Status",
    description: "Is everything running smoothly? This tab shows the health of every component — database, AI models, memory, search, and more. Grace's immune system monitors and heals problems automatically.",
    tips: ["Green = healthy, Yellow = warning, Red = needs attention", "Grace can self-heal most issues automatically", "Check healing history to see what was fixed"],
  },
  "learn-heal": {
    title: "Learn & Heal — Self-Improvement",
    description: "Watch Grace learn and heal herself. See what she's learned recently, what problems she's fixed, and what skills she's developing. This is Grace's growth dashboard.",
    tips: ["See learning progress over time", "Review healing actions and their outcomes", "Check which skills Grace has mastered"],
  },
};

export default function TabGuide({ tabId }) {
  const [show, setShow] = useState(false);
  const guide = GUIDES[tabId];

  if (!guide) return null;

  return (
    <>
      <button onClick={() => setShow(!show)} title="What is this tab?" style={{
        background: 'none', border: '1px solid #444', borderRadius: 12,
        color: '#888', fontSize: 11, padding: '2px 8px', cursor: 'pointer',
        marginLeft: 8,
      }}>
        ?
      </button>

      {show && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 100,
          background: '#0f3460', border: '1px solid #333', borderRadius: 8,
          padding: 16, boxShadow: '0 8px 24px rgba(0,0,0,.5)',
          margin: '4px 16px',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: '#eee', margin: '0 0 8px' }}>
              {guide.title}
            </h3>
            <button onClick={() => setShow(false)} style={{
              background: 'none', border: 'none', color: '#888',
              fontSize: 16, cursor: 'pointer',
            }}>✕</button>
          </div>
          <p style={{ fontSize: 13, color: '#ccc', lineHeight: 1.6, margin: '0 0 12px' }}>
            {guide.description}
          </p>
          {guide.tips && (
            <div>
              <div style={{ fontSize: 11, color: '#888', fontWeight: 600, marginBottom: 4 }}>TIPS:</div>
              {guide.tips.map((tip, i) => (
                <div key={i} style={{ fontSize: 12, color: '#aaa', marginBottom: 3 }}>
                  💡 {tip}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </>
  );
}
