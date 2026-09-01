import api from "./api";

export const uploadDocuments = async (formData: FormData, username: string) => {
  return api.post("/upload_docs", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
      "x-username": username,
    },
  });
};

export const getJobStatus = async (jobId: string) => {
  return api.get(`job_status/${jobId}`);
};
