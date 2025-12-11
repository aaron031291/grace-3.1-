import { useState, useEffect, useRef } from "react";
import ChatList from "./ChatList";
import ChatWindow from "./ChatWindow";
import "./ChatTab.css";

export default function ChatTab() {
  const [chats, setChats] = useState([]);
  const [selectedChatId, setSelectedChatId] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchChats();
  }, []);

  const fetchChats = async () => {
    try {
      setLoading(true);
      const response = await fetch("http://localhost:8000/chats?limit=50");
      const data = await response.json();
      setChats(data.chats);
      if (data.chats.length > 0 && !selectedChatId) {
        setSelectedChatId(data.chats[0].id);
      }
    } catch (error) {
      console.error("Failed to fetch chats:", error);
    } finally {
      setLoading(false);
    }
  };

  const createNewChat = async () => {
    try {
      const response = await fetch("http://localhost:8000/chats", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: "New Chat",
          description: "New conversation",
        }),
      });
      const newChat = await response.json();
      setChats([newChat, ...chats]);
      setSelectedChatId(newChat.id);
    } catch (error) {
      console.error("Failed to create chat:", error);
    }
  };

  const deleteChat = async (chatId) => {
    try {
      await fetch(`http://localhost:8000/chats/${chatId}`, {
        method: "DELETE",
      });
      const updatedChats = chats.filter((c) => c.id !== chatId);
      setChats(updatedChats);
      if (selectedChatId === chatId) {
        setSelectedChatId(updatedChats.length > 0 ? updatedChats[0].id : null);
      }
    } catch (error) {
      console.error("Failed to delete chat:", error);
    }
  };

  const updateChatTitle = async (chatId, newTitle) => {
    try {
      const response = await fetch(`http://localhost:8000/chats/${chatId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: newTitle }),
      });
      const updated = await response.json();
      setChats(chats.map((c) => (c.id === chatId ? updated : c)));
    } catch (error) {
      console.error("Failed to update chat:", error);
    }
  };

  return (
    <div className="chat-tab">
      <ChatList
        chats={chats}
        selectedChatId={selectedChatId}
        onSelectChat={setSelectedChatId}
        onCreateChat={createNewChat}
        onDeleteChat={deleteChat}
        onUpdateTitle={updateChatTitle}
        loading={loading}
      />
      <ChatWindow chatId={selectedChatId} onChatCreated={fetchChats} />
    </div>
  );
}
