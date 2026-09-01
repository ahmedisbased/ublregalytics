import api from "./api";

export const uploadImagesForExcel = async (formData: FormData) => {
  return api.post("extract-financials", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
    responseType: "blob",
  });
};
