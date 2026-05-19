import axios from "axios";

const api = axios.create({
  baseURL:
    import.meta.env.VITE_API_BASE_URL ||
    "https://bca-chatbot-fkbfd2cfa2b9gvh0.uaenorth-01.azurewebsites.net/",
  headers: {
    "Content-Type": "application/json",
  },
});

export default api;
