import api from "./api";

export interface XmlGeneratorParams {
  account_number: string;
  transaction_id: string | null;
  from_date: string | null;
  to_date: string | null;
}

export const generateXml = async (params: XmlGeneratorParams) => {
  return api.post<{ xml: string }>("/generate_xml", params);
};
