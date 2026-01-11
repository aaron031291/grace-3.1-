import { useState, useEffect } from "react";
import ChatList from "./ChatList";
import ChatWindow from "./ChatWindow";
import "./ChatTab.css";

export default function ChatTab() {
  const [chats, setChats] = useState([]);
  const [selectedChatId, setSelectedChatId] = useState(null);
  const [selectedFolder, setSelectedFolder] = useState(""); // Track selected folder
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchChats();
  }, [selectedFolder]); // Refetch chats when folder changes

  const fetchChats = async () => {
    try {
      setLoading(true);
      // Filter chats by selected folder
      const folderParam = selectedFolder
        ? `&folder_path=${encodeURIComponent(selectedFolder)}`
        : "";
      const response = await fetch(
        `http://localhost:8000/chats?limit=50${folderParam}`
      );
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      const data = await response.json();
      // Handle undefined or missing chats array
      setChats(data?.chats || []);
      if (data?.chats?.length > 0 && !selectedChatId) {
        setSelectedChatId(data.chats[0].id);
      } else if (!data?.chats || data.chats.length === 0) {
        setSelectedChatId(null);
      }
    } catch (error) {
      console.error("Failed to fetch chats:", error);
      setChats([]);
      setSelectedChatId(null);
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
          folder_path: selectedFolder, // Include folder path when creating chat
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
        selectedFolder={selectedFolder}
        onSelectChat={setSelectedChatId}
        onSelectFolder={setSelectedFolder}
        onCreateChat={createNewChat}
        onDeleteChat={deleteChat}
        onUpdateTitle={updateChatTitle}
        loading={loading}
      />
      <ChatWindow
        chatId={selectedChatId}
        folderPath={selectedFolder}
        onChatCreated={fetchChats}
      />
    </div>
  );
}
