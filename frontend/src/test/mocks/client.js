import { vi } from 'vitest';

export const GOOGLE_LOGIN_URL = 'http://localhost:8000/accounts/google/login/';

export const fetchDashboard = vi.fn();
export const fetchComments = vi.fn();

export const fetchPosts = vi.fn();
export const fetchPost = vi.fn();
export const createPost = vi.fn();
export const updatePost = vi.fn();
export const deletePost = vi.fn();

export const fetchTags = vi.fn();
export const fetchTag = vi.fn();
export const createTag = vi.fn();
export const updateTag = vi.fn();
export const deleteTag = vi.fn();

export const fetchUsers = vi.fn();
export const fetchUser = vi.fn();

export const fetchCurrentUser = vi.fn();
export const updateProfile = vi.fn();
export const fetchUserComments = vi.fn();
export const loginUser = vi.fn();
export const registerUser = vi.fn();
export const logoutUser = vi.fn();
export const voteComment = vi.fn();
export const createComment = vi.fn();
export const updateComment = vi.fn();
export const deleteComment = vi.fn();

export const resendVerification = vi.fn();

export const fetchCsrf = vi.fn();

export default { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() };
