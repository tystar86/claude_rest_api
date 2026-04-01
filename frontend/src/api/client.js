import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000/api",
  withCredentials: true,
});

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(";").shift();
}

async function ensureCsrfCookie() {
  const token = getCookie("csrftoken");
  if (token) return token;
  await api.get("/auth/csrf/");
  return getCookie("csrftoken");
}

api.interceptors.request.use(async (config) => {
  if (["post", "put", "patch", "delete"].includes(config.method)) {
    const token = await ensureCsrfCookie();
    if (token) config.headers["X-CSRFToken"] = token;
  }
  return config;
});

export const fetchDashboard = () => api.get("/dashboard/").then((r) => r.data);
export const fetchComments = (page = 1) => api.get(`/comments/?page=${page}`).then((r) => r.data);

export const fetchPosts = (page = 1) => api.get(`/posts/?page=${page}`).then((r) => r.data);
export const fetchPost = (slug) => api.get(`/posts/${slug}/`).then((r) => r.data);
export const createPost = (payload) => api.post("/posts/", payload).then((r) => r.data);
export const updatePost = (slug, payload) => api.patch(`/posts/${slug}/`, payload).then((r) => r.data);
export const deletePost = (slug) => api.delete(`/posts/${slug}/`).then((r) => r.data);

export const fetchTags = (page = 1) => api.get(`/tags/?page=${page}`).then((r) => r.data);
export const fetchTag = (slug, page = 1) => api.get(`/tags/${slug}/?page=${page}`).then((r) => r.data);
export const createTag = (name) => api.post("/tags/", { name }).then((r) => r.data);
export const updateTag = (slug, name) => api.patch(`/tags/${slug}/`, { name }).then((r) => r.data);
export const deleteTag = (slug) => api.delete(`/tags/${slug}/`).then((r) => r.data);

export const fetchUsers = (page = 1) => api.get(`/users/?page=${page}`).then((r) => r.data);
export const fetchUser = (username, page = 1) => api.get(`/users/${username}/?page=${page}`).then((r) => r.data);

export const fetchCurrentUser = () => api.get("/auth/user/").then((r) => r.data);
export const loginUser = (email, password) => api.post("/auth/login/", { email, password }).then((r) => r.data);
export const registerUser = (email, username, password) => api.post("/auth/register/", { email, username, password }).then((r) => r.data);
export const logoutUser = () => api.post("/auth/logout/").then((r) => r.data);
export const voteComment = (commentId, vote) => api.post(`/comments/${commentId}/vote/`, { vote }).then((r) => r.data);
export const createComment = (slug, body, parentId = null) =>
  api.post(`/posts/${slug}/comments/`, { body, parent_id: parentId }).then((r) => r.data);
export const updateComment = (commentId, body) =>
  api.patch(`/comments/${commentId}/`, { body }).then((r) => r.data);
export const deleteComment = (commentId) =>
  api.delete(`/comments/${commentId}/delete/`).then((r) => r.data);

export const fetchCsrf = () => api.get("/auth/csrf/").then((r) => r.data);

export default api;
