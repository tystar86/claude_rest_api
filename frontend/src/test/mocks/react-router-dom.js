import { vi } from 'vitest';

export const Link = ({ children, to }) => <a href={to}>{children}</a>;
export const useNavigate = () => vi.fn();
export const useSearchParams = () => [new URLSearchParams(), vi.fn()];
export const MemoryRouter = ({ children }) => <>{children}</>;
