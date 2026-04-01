import { Routes, Route, Navigate, useLocation } from "react-router-dom";
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
import Login from "./pages/Login";
import Register from "./pages/Register";

export default function App() {
  const location = useLocation();
  const isDashboard = location.pathname === "/dashboard";
  const isTagsRoute = location.pathname.startsWith("/tags");
  const isPostsRoute = location.pathname.startsWith("/posts");
  const isUsersRoute = location.pathname.startsWith("/users");
  const isCommentsRoute = location.pathname.startsWith("/comments");
  const useEmbeddedNavbar = isDashboard || isTagsRoute || isPostsRoute || isUsersRoute || isCommentsRoute;
  const useFluidLayout = isDashboard || isTagsRoute || isPostsRoute || isUsersRoute || isCommentsRoute;

  return (
    <AuthProvider>
      <div className="app-shell">
        <div className={useFluidLayout ? "container-fluid px-0 py-0" : "container py-4"}>
          {!useEmbeddedNavbar && <Navbar />}
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
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
          </Routes>
        </div>
      </div>
    </AuthProvider>
  );
}
