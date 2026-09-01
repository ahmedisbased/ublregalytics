import api from "./api";
import type { Permission } from './authPermissions';

type LoginPayload = {
  username: string;
  password: string;
};

type LoginResponse = {
  access_token: string;
  refresh_token: string;
  permissions: Permission[];
};

export const loginUser = async ({ username, password }: LoginPayload) => {
  console.log(`inside loginUser ${api.defaults.baseURL}`)
  const { data } = await api.post<LoginResponse>("login", {
    username,
    password,
  });
  console.log(`data is ${data}`)
  return data;
};

// Revoke the session server-side, then clear local storage. Best-effort: even
// if the network call fails we still clear the client so the user is logged out
// locally.
export const logoutUser = async () => {
  const refresh_token = localStorage.getItem("refresh_token");
  try {
    await api.post("logout", { refresh_token });
  } catch {
    /* ignore - clear locally regardless */
  } finally {
    localStorage.removeItem("token");
    localStorage.removeItem("refresh_token");
  }
};
