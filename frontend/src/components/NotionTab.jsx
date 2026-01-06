import { useEffect, useState } from "react";
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import "./NotionTab.css";

const STORAGE_KEY = "notion-kanban-board";

function DraggableCard({ card, columnId, onDelete }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: card.id,
    data: { type: "card", card, columnId },
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="kanban-card"
      {...attributes}
      {...listeners}
    >
      <div className="card-content">
        <h4>{card.title}</h4>
      </div>
      <button
        className="card-delete"
        onClick={(e) => {
          e.stopPropagation();
          onDelete(columnId, card.id);
        }}
        onPointerDown={(e) => e.stopPropagation()}
      >
        ✕
      </button>
    </div>
  );
}

function Column({ column, onDelete, activeId }) {
  const cardIds = column.cards.map((c) => c.id);
  const { setNodeRef } = useSortable({
    id: column.id,
    data: { type: "column", column },
    disabled: true,
  });

  const isOverColumn =
    activeId &&
    !cardIds.includes(activeId) &&
    activeId.toString().includes("card-");

  return (
    <div
      ref={setNodeRef}
      className={`kanban-column ${isOverColumn ? "drag-over" : ""}`}
    >
      <div className="column-header">
        <h3>{column.title}</h3>
        <span className="card-count">{column.cards.length}</span>
      </div>

      <SortableContext items={cardIds} strategy={verticalListSortingStrategy}>
        <div className="cards-list">
          {column.cards.length === 0 ? (
            <div className="empty-column">Drop cards here</div>
          ) : (
            column.cards.map((card) => (
              <DraggableCard
                key={card.id}
                card={card}
                columnId={column.id}
                onDelete={onDelete}
              />
            ))
          )}
        </div>
      </SortableContext>
    </div>
  );
}

export default function NotionTab() {
  const defaultBoard = {
    columns: [
      {
        id: "col-1",
        title: "📋 To Do",
        cards: [
          { id: "card-1", title: "Plan project structure" },
          { id: "card-2", title: "Setup development environment" },
        ],
      },
      {
        id: "col-2",
        title: "🔄 In Progress",
        cards: [{ id: "card-3", title: "Implement chat history feature" }],
      },
      {
        id: "col-3",
        title: "✅ Done",
        cards: [
          { id: "card-4", title: "Initialize project" },
          { id: "card-5", title: "Create database schema" },
        ],
      },
    ],
  };

  const [board, setBoard] = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? JSON.parse(saved) : defaultBoard;
  });

  const [newCardTitle, setNewCardTitle] = useState("");
  const [selectedColumnId, setSelectedColumnId] = useState("col-1");
  const [activeId, setActiveId] = useState(null);

  // Persist board changes
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(board));
  }, [board]);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      distance: 8,
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragStart = (event) => {
    setActiveId(event.active.id);
  };

  const handleDragCancel = () => {
    setActiveId(null);
  };

  const handleDragEnd = (event) => {
    setActiveId(null);

    const { active, over } = event;

    if (!over) return;

    if (active.id === over.id) return;

    const newBoard = JSON.parse(JSON.stringify(board));

    // Find source position
    let sourceColumnIndex = -1;
    let sourceCardIndex = -1;

    for (let i = 0; i < newBoard.columns.length; i++) {
      const cardIndex = newBoard.columns[i].cards.findIndex(
        (c) => c.id === active.id
      );
      if (cardIndex !== -1) {
        sourceColumnIndex = i;
        sourceCardIndex = cardIndex;
        break;
      }
    }

    if (sourceColumnIndex === -1) return;

    const card = newBoard.columns[sourceColumnIndex].cards[sourceCardIndex];

    // Find destination position
    let destColumnIndex = -1;
    let destCardIndex = 0;

    for (let i = 0; i < newBoard.columns.length; i++) {
      const cardIndex = newBoard.columns[i].cards.findIndex(
        (c) => c.id === over.id
      );
      if (cardIndex !== -1) {
        destColumnIndex = i;
        destCardIndex = cardIndex;
        break;
      }
    }

    // If not dropped on a card, find the column
    if (destColumnIndex === -1) {
      for (let i = 0; i < newBoard.columns.length; i++) {
        if (newBoard.columns[i].id === over.id) {
          destColumnIndex = i;
          destCardIndex = newBoard.columns[i].cards.length;
          break;
        }
      }
    }

    if (destColumnIndex === -1) return;

    // Remove from source
    newBoard.columns[sourceColumnIndex].cards.splice(sourceCardIndex, 1);

    // Add to destination
    newBoard.columns[destColumnIndex].cards.splice(destCardIndex, 0, card);

    setBoard(newBoard);
  };

  const addCard = () => {
    if (!newCardTitle.trim()) return;

    const newBoard = JSON.parse(JSON.stringify(board));
    const columnIndex = newBoard.columns.findIndex(
      (c) => c.id === selectedColumnId
    );

    if (columnIndex !== -1) {
      const maxId = Math.max(
        ...newBoard.columns.flatMap((col) =>
          col.cards.map((c) => parseInt(c.id.split("-")[1]) || 0)
        ),
        0
      );

      newBoard.columns[columnIndex].cards.push({
        id: `card-${maxId + 1}`,
        title: newCardTitle,
      });

      setBoard(newBoard);
      setNewCardTitle("");
    }
  };

  const deleteCard = (columnId, cardId) => {
    const newBoard = JSON.parse(JSON.stringify(board));
    const columnIndex = newBoard.columns.findIndex((c) => c.id === columnId);

    if (columnIndex !== -1) {
      newBoard.columns[columnIndex].cards = newBoard.columns[
        columnIndex
      ].cards.filter((c) => c.id !== cardId);
      setBoard(newBoard);
    }
  };

  return (
    <div className="notion-tab">
      <div className="notion-header">
        <h2>📌 Task Management</h2>
        <p>Organize your tasks with drag-and-drop Kanban board</p>
      </div>

      <div className="add-card-section">
        <select
          value={selectedColumnId}
          onChange={(e) => setSelectedColumnId(e.target.value)}
          className="column-select"
        >
          {board.columns.map((col) => (
            <option key={col.id} value={col.id}>
              {col.title}
            </option>
          ))}
        </select>
        <input
          type="text"
          value={newCardTitle}
          onChange={(e) => setNewCardTitle(e.target.value)}
          onKeyPress={(e) => {
            if (e.key === "Enter") {
              addCard();
            }
          }}
          placeholder="Add a new task..."
          className="add-card-input"
        />
        <button onClick={addCard} className="add-card-button">
          + Add Task
        </button>
      </div>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragCancel={handleDragCancel}
        onDragEnd={handleDragEnd}
      >
        <div className="kanban-container">
          {board.columns.map((column) => (
            <Column
              key={column.id}
              column={column}
              onDelete={deleteCard}
              activeId={activeId}
            />
          ))}
        </div>

        <DragOverlay>
          {activeId ? (
            <div className="kanban-card dragging-overlay">
              <div className="card-content">
                <h4>
                  {
                    board.columns
                      .flatMap((c) => c.cards)
                      .find((c) => c.id === activeId)?.title
                  }
                </h4>
              </div>
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>

      <div className="kanban-footer">
        <p>💡 Drag cards between columns to update their status</p>
      </div>
    </div>
  );
}
