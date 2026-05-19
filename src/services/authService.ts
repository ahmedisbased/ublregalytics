import api from "./api";

type LoginPayload = {
  email: string;
  password: string;
};

type LoginResponse = {
  success: boolean;
  role?: "USER" | "ADMIN";
};

export const loginUser = async ({ email, password }: LoginPayload) => {
  const { data } = await api.post<LoginResponse>("login", {
    email,
    password,
  });

  return data;
};
