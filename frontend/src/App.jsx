import { Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import Navbar from "./components/Navbar";
import Dashboard from "./pages/Dashboard";
import CommentList from "./pages/CommentList";
import PostList from "./pages/PostList";
import PostDetail from "./pages/PostDetail";
import TagList from "./pages/TagList";
import TagDetail from "./pages/TagDetail";
import UserList from "./pages/UserList";
import UserDetail from "./pages/UserDetail";
import UserProfile from "./pages/UserProfile";
import Login from "./pages/Login";
import Register from "./pages/Register";

export default function App() {
  return (
    <AuthProvider>
      <div className="app-shell">
        <Navbar />
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/comments" element={<CommentList />} />
          <Route path="/posts" element={<PostList />} />
          <Route path="/posts/:slug" element={<PostDetail />} />
          <Route path="/tags" element={<TagList />} />
          <Route path="/tags/:slug" element={<TagDetail />} />
          <Route path="/users" element={<UserList />} />
          <Route path="/users/:username" element={<UserDetail />} />
          <Route path="/profile" element={<UserProfile />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
        </Routes>
      </div>
    </AuthProvider>
  );
}
