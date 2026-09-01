import api from "./api";
export interface XmlGeneratorParams {
  main_account: string;
  transaction_number: string | null;
  from_date: string | null;
  to_date: string | null;
}

export const generateXml = async (params: XmlGeneratorParams) => {
  return api.post<{ xml: string }>("/generate-xml", params);
};
