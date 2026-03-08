import React, { useEffect, useRef } from "react";
import "./ContextMenu.css";
import { brainCall } from "../api/brain-client";

/**
 * ContextMenu
 * A globally available right-click overlay providing "Brain Operations"
 * over files, folders, and cognitive items.
 */
function ContextMenu({ x, y, visible, item, onClose }) {
    const menuRef = useRef(null);

    // Close when clicking outside
    useEffect(() => {
        const handleClickOutside = (e) => {
            if (menuRef.current && !menuRef.current.contains(e.target)) {
                onClose();
            }
        };
        if (visible) {
            document.addEventListener("mousedown", handleClickOutside);
        }
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, [visible, onClose]);

    if (!visible || !item) return null;

    // Actions routed to Grace's Brain Mesh
    const actions = [
        {
            label: "🧠 Ask Grace to Analyze",
            icon: "🔍",
            onClick: async () => {
                try {
                    alert(`Triggering analysis on: ${item.name || item.path}`);
                    await brainCall("code", "analyze_file", { file_path: item.path });
                    onClose();
                } catch (e) {
                    console.error(e);
                }
            },
        },
        {
            label: "🧬 Trigger Self-Healing",
            icon: "🩹",
            onClick: async () => {
                try {
                    alert(`Injecting immune pulse into: ${item.name || item.path}`);
                    await brainCall("deterministic", "heal_target", { target: item.path });
                    onClose();
                } catch (e) {
                    console.error(e);
                }
            },
        },
        {
            label: "🏗️ Send to Proposer Architecture",
            icon: "📐",
            onClick: () => {
                alert("Pushed to Architecture Proposer context!");
                // We typically would push this to a global context or recoil store here
                onClose();
            },
        },
        {
            label: "🔗 Map Dependencies",
            icon: "🕸️",
            onClick: async () => {
                try {
                    alert(`Extracting semantic topology for: ${item.name || item.path}`);
                    await brainCall("code", "find_dependencies", { file_path: item.path });
                    onClose();
                } catch {
                    onClose();
                }
            },
        },
    ];

    return (
        <div
            ref={menuRef}
            className="context-menu"
            style={{ top: `${y}px`, left: `${x}px` }}
        >
            <div className="context-header">
                <span className="context-item-type">{item.type === "dir" ? "Directory" : "File"}</span>
                <span className="context-item-name">{item.name || item.path}</span>
            </div>
            <ul className="context-options">
                {actions.map((act, idx) => (
                    <li key={idx} className="context-option" onClick={act.onClick}>
                        <span className="icon">{act.icon}</span>
                        {act.label}
                    </li>
                ))}
            </ul>
        </div>
    );
}

export default ContextMenu;
