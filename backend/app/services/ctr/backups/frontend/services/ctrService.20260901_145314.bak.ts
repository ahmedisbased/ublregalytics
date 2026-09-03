import api from "./api";

export interface CsvGeneratorParams {
  transaction_date: string;
  cr_dr_flag: "DR" | "CR";
  entity_individual_flag: "ENTITY" | "INDIVIDUAL";
}

export interface Checking {
  cr_dr_flag: "DR" | "CR";

}

export interface XmlGeneratorParams {
  filename : string;
  fileData : Blob | null;
  transaction_date: string;
  cr_dr_flag: "DR" | "CR";
  entity_individual_flag: "ENTITY" | "INDIVIDUAL";

}

export const uploadFileStream = async (form : FormData) => {
  // console.log(`cr_dr_flag name is ${cr_dr_flag}}`)
  // let response = api.post("/ctr", {cr_dr_flag, transaction_date,entity_individual_flag, file}
  //  )

  for (let [key,value] of form.entries()) {
    if (value instanceof File) {
      console.log(`${key} : File (${value.name})`)
    } else {
      console.log(`${key} : ${value}`)
    }
  }
  let response = api.post("/ctr" , form, {
    responseType : 'blob',
    headers : {
      'Content-Type' : 'multipart/form-data'
    }
  }
)
  return response
}
export const generateXml = async (formData: FormData) => {
  
  console.log("trying to post the request with params : ", formData)
  console.log(`this is just before the api call`)
  console.log(`the api is this ${api}`)
  let response =  api.post("/ctr", formData, {
    responseType: "arraybuffer",
  })
  console.log(` the response after the call is ${response}`)
  return response
};
export const generateCsv = async (params: CsvGeneratorParams) => {
  console.log("trying to post the request with params : ", params)

  return api.post("/csv", params, {
    responseType: "arraybuffer",
  });
};
