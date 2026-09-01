
def get_entity_query3(account_number):
    
  q = rf""" WITH ENTITY_MAIN_ACCT AS ( 
    SELECT  
        C.ACCT_SROGT_ID, 
        C.ACCT_TITL, 
        CAST(D.E_ML_ADDR AS VARCHAR(100)) AS E_ML_ADDR,
        OREPLACE(COALESCE(D.MBL_NUM, D.PHN_BUSN, D.PHN_RSDNC), '[^0-9]') AS MOBILE,
        D.IDNTFTN_VAL, 
        D.CUST_SROGT_ID, 
        CAST(REGEXP_REPLACE(OTRANSLATE(NULLIF(D.PERM_ADDR,''), ',?\/()-',''), '\s{2,}', '') AS VARCHAR(200)) AS PERM_ADDR,
        CAST(REGEXP_REPLACE(OTRANSLATE(D.MLG_ADDR, ',?\/()-',''), '\s{2,}', '') AS VARCHAR(200)) AS MLG_ADDR
    FROM DP_SDMVW_DFDN.DIM_RTAIL_BNK_ACCT_VW C 
    INNER JOIN DP_SDMVW_DFDN.DIM_CUST_VW D 
        ON D.CUST_SROGT_ID = C.CUST_SROGT_ID 
       AND D.SYSTEM_CODE = 'CBS' 
    WHERE C.ACCT_SROGT_ID = '{account_number}'
    ), 

    DIM_CUST AS ( 
      SELECT  
          DC.CUST_SROGT_ID, 
          DC.IDNTFTN_VAL, 
          CAST(DC.E_ML_ADDR AS VARCHAR(100)) AS E_ML_ADDR,
          OREPLACE(COALESCE(DC.MBL_NUM, DC.PHN_BUSN, DC.PHN_RSDNC), '[^0-9]') AS NEW_MOBILE,
          CASE 
              WHEN NEW_MOBILE LIKE '0092%' THEN SUBSTR(NEW_MOBILE,5) 
              WHEN NEW_MOBILE LIKE '+92%'  THEN SUBSTR(NEW_MOBILE,4) 
              WHEN NEW_MOBILE LIKE '3%'    THEN '0'||NEW_MOBILE 
              WHEN NEW_MOBILE LIKE '92%' AND LENGTH(NEW_MOBILE)=13 THEN SUBSTR(NEW_MOBILE,3) 
              WHEN NEW_MOBILE LIKE '92%' AND LENGTH(NEW_MOBILE)=12 THEN '0'||SUBSTR(NEW_MOBILE,3) 
              ELSE NEW_MOBILE 
          END AS MOBILE, 
          CAST(REGEXP_REPLACE(OTRANSLATE(NULLIF(DC.PERM_ADDR,''), ',?\/()-',''), '\s{2,}', '') AS VARCHAR(200)) AS PERM_ADDR,
          CAST(REGEXP_REPLACE(OTRANSLATE(DC.MLG_ADDR, ',?\/()-',''), '\s{2,}', '') AS VARCHAR(200)) AS MLG_ADDR, 
          DC.SYSTEM_CODE, 
          DC.CUST_TYPE_EDW_ID, 
          C.CUST_TYPE_DESC,  
          C.CUST_TYPE_CD,
          ROW_NUMBER() OVER(PARTITION BY DC.CUST_SROGT_ID, DC.SYSTEM_CODE ORDER BY DC.START_DATE DESC) AS RN 
      FROM DP_SDMVW_DFDN.DIM_CUST_VW DC 
      LEFT JOIN DP_SDMT_DFDN.DIM_CUST_TYPE_SS C 
          ON C.CUST_TYPE_EDW_ID = DC.CUST_TYPE_EDW_ID AND C.SYSTEM_CODE = 'CBS' 
    INNER JOIN ENTITY_MAIN_ACCT EM 
      ON (
          COALESCE(DC.PERM_ADDR, 'abc') = COALESCE(EM.PERM_ADDR, 'abc')
          OR COALESCE(
              OREPLACE(COALESCE(DC.MBL_NUM, DC.PHN_BUSN, DC.PHN_RSDNC), '[^0-9]'),
              '123'
            ) = COALESCE(NULLIF(EM.MOBILE,''), 'x12x')
          OR COALESCE(DC.IDNTFTN_VAL, 'abc') = COALESCE(EM.IDNTFTN_VAL, 'abc')
          OR COALESCE(DC.MLG_ADDR, 'abc') = COALESCE(EM.MLG_ADDR, 'abc')
          OR COALESCE(DC.E_ML_ADDR, 'abc') = COALESCE(EM.E_ML_ADDR, 'abc')
      )
      WHERE DC.SYSTEM_CODE = 'CBS'
    ) ,

    RB_RELATED_ACCTS AS ( 
        SELECT DISTINCT 
            C.ACCT_SROGT_ID  AS ACCT_NO 
        FROM ENTITY_MAIN_ACCT EM
        INNER JOIN DIM_CUST D ON D.SYSTEM_CODE = 'CBS'
        LEFT JOIN DP_SDMVW_DFDN.DIM_RTAIL_BNK_ACCT_VW C 
            ON D.CUST_SROGT_ID = C.CUST_SROGT_ID 
        WHERE 1=1
      AND D.CUST_TYPE_CD IN ('03','31','32','33','34','35','36','37','38')
      and C.ACCT_SROGT_ID  =  '{account_number}'
    ) ,
    AMOUNT AS (
          SELECT CAST(SUM(CR_AMOUNT) AS DECIMAL(38,2)) AS cr_amt, CAST(SUM (DR_AMOUNT) AS DECIMAL(38,2)) as Dr_amt, ACCT_SROGT_ID
          FROM (
    select DISTINCT 
          CASE WHEN CR_DR_IND = 'C' and SRC_TYP <> 'NI'  THEN (TSACTN_AMT) END AS CR_AMOUNT,
          CASE WHEN CR_DR_IND = 'D' THEN (TSACTN_AMT) END AS DR_AMOUNT, ACCT_SROGT_ID,TSACTN_ID
    from DP_SDMVW_DFDN.FCT_RTAIL_BNK_TSACTN_VW txn INNER JOIN RB_RELATED_ACCTS RRA
    ON TXN.ACCT_SROGT_ID = RRA.ACCT_NO
    WHERE  1 =1   
    --AND ACCT_SROGT_ID=   '{account_number}'   -- '291808031' --: '{account_number}'  
    AND RVSL_SEQ_NUM IS NULL 
    AND Reveral_IND = 'N'
    and  TO_CHAR(TSACTN_DT,'YYYY-MM-DD')  between coalesce(NULL  , cast(add_months( CURRENT_DATE-1 , -36) as varchar(15)) ) 
              and coalesce(NULL  , cast(CURRENT_DATE-1 as varchar(15)) )
      )  A
      group by ACCT_SROGT_ID ) , 

      CLEAN_NAME AS (
        SELECT 
            REGEXP_REPLACE(D.CUST_NAME , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') AS NAME_CLEAN,
            D.*
        FROM DP_SDMVW_DFDN.DIM_CUST_VW D
      ),
      DIM_CUST_VW AS (
        SELECT  
            D.CUST_SROGT_ID,
            D.FTHR_NAME AS mothers_name, 
            D.IDNTFTN_VAL AS ssn, 
            D.CTRY_OF_NTLTY AS nationality1,
            D.GNDR AS gender,
            TRIM(SUBSTRING(NAME_CLEAN FROM 1 FOR POSITION(' ' IN NAME_CLEAN || ' ') - 1)) AS first_name,
            CASE 
                WHEN TRIM(SUBSTRING(NAME_CLEAN FROM POSITION(' ' IN NAME_CLEAN || ' ') + 1)) = '' 
                THEN TRIM(SUBSTRING(NAME_CLEAN FROM 1 FOR POSITION(' ' IN NAME_CLEAN || ' ') - 1))
                ELSE TRIM(SUBSTRING(NAME_CLEAN FROM POSITION(' ' IN NAME_CLEAN || ' ') + 1))
            END AS last_name,
            D.CUST_TYPE_EDW_ID,
            D.CTRY_OF_NTLTY AS to_country,  
            D.CUST_SROGT_ID AS CUST_NUM, 
            CAST(D.DT_OF_BIRTH AS VARCHAR(20)) || 'T00:00:00' AS birthdate,
            CASE WHEN D.MBL_NUM IS NOT NULL THEN 'PAPVT' ELSE 'PAOFF' END AS tph_contact_type,
            CASE WHEN D.MBL_NUM IS NOT NULL THEN 'COMOB' ELSE 'COOTH' END AS tph_communication_type,
            CASE 
                WHEN D.MBL_NUM IS NOT NULL AND (SUBSTR(D.MBL_NUM,0,2) = '92' OR SUBSTR(D.MBL_NUM,1,3) = '92') THEN '92'
                WHEN LENGTH(SUBSTR(D.MBL_NUM,2,12)) = 10 OR LENGTH(SUBSTR(D.MBL_NUM,3,13)) = 10 THEN '92'
                WHEN D.CTRY_OF_NTLTY = 'PK' THEN '92'
                ELSE SUBSTR(D.MBL_NUM,0,2) 
            END AS tph_country_prefix,
            COALESCE(REGEXP_SUBSTR(D.MBL_NUM,'3.*'), SUBSTR(D.PHN_BUSN,2,12)) AS tph_number,
            CASE WHEN D.PERM_ADDR IS NOT NULL THEN 'PAPVT' ELSE 'PAOFF' END AS address_type,
            COALESCE(D.MLG_ADDR, D.PERM_ADDR) AS address,
            D.CTRY_OF_NTLTY AS country_code, 
            CASE 
                WHEN D.RSDNTL_CITY = '0' OR D.RSDNTL_CITY IS NULL 
                THEN TRIM(REGEXP_SUBSTR(location,'[A-Z a-z]+')) 
                ELSE D.RSDNTL_CITY 
            END AS city,
            COALESCE(D.RGN_NAME,
                CASE FMC.STATE_LOC
                    WHEN 'NW' THEN 'KPK'
                    WHEN 'AK' THEN 'AZAD KASHMIR'
                    WHEN 'PJ' THEN 'PUNJAB'
                    WHEN 'SD' THEN 'SINDH'
                    WHEN 'BL' THEN 'BALOCHISTAN'
                    WHEN 'IS' THEN 'ISLAMABAD'
                    WHEN 'GB' THEN 'GILGIT-BALISTAN'
                    WHEN 'FA' THEN 'GILGIT-BALISTAN'
                END
            ) AS state,
            'UNITED BANK LIMITED' AS institution_name,  
            'UNILPKKA' AS swift, 
            'PK' AS institution_country,
            'ETPVT' AS incorporation_legal_form,
        e.CUST_TYPE_CD as CUST_TYPE_CD,
        e.CUST_TYPE_DESC as CUST_TYPE_DESC
        FROM CLEAN_NAME D
        INNER JOIN dp_wrk_cbs.fm_client_daily FMC ON D.CUST_SROGT_ID = FMC.client_no AND D.system_code = 'CBS'
        INNER JOIN DP_SDMT_DFDN.DIM_CUST_TYPE_SS E ON E.CUST_TYPE_EDW_ID = D.CUST_TYPE_EDW_ID
      )
      -- Mandate Client
      SELECT DISTINCT DIM_ACCT.ACCT_SROGT_ID AS ACCT_NUM, DIM_ACCT.ACCT_DESC,
          'MANDATE_CLIENT' AS TYP, MA.CLIENT_NO, 'ARPYS' AS ROLE_OUTER,    dc.CUST_SROGT_ID,
          dc.mothers_name,       dc.ssn,       dc.nationality1,       dc.gender,       dc.first_name,       dc.last_name,       dc.CUST_TYPE_CD,
          dc.CUST_TYPE_DESC,       dc.to_country,       dc.CUST_NUM,       dc.birthdate,       dc.tph_contact_type,
          dc.tph_communication_type,       dc.tph_country_prefix,       dc.tph_number,       dc.address_type,
          dc.address,       dc.country_code,       dc.city,       dc.state,
          dc.institution_name,       dc.swift,       dc.institution_country,      dc.incorporation_legal_form,
            b.BRNCH_DESC AS branch, 
            COALESCE(B.CITY_NAME,B.BRNCH_DESC) AS BR_CITY_NAME, 
            b.Branch_Code AS teller,
            DIM_ACCT.ACCT_SROGT_ID AS account_, 
            DIM_ACCT.IBAN_NUM, 
            DIM_ACCT.CURY_EDW_ID AS currency_code,
            DIM_ACCT.ACCT_TITL AS account_name,
            DIM_ACCT.ACCT_TITL AS ENTITY_NAME, 
            DIM_ACCT.SRC_OF_FUND AS business, 
            CASE 
                WHEN CUST_TYPE_CD IN ('14','06','13','16','15','07','04','30','19','28','25','02','09','38','03',
                                      '05','10','01','26','21','18','12','24','20','29','22','23','08','27','31') THEN 'ARCTA'
                WHEN JOIN_ACCT_FLG = '1' THEN 'ARJTA'
                WHEN CUST_TYPE_CD = '11' THEN 'ARMRB' 
                ELSE 'ARCTA' 
            END AS Role_, 
            CASE 
                WHEN DIM_ACCT.DEP_TYPE = 'C' THEN 'ATCUR' 
                WHEN DIM_ACCT.dep_Type = 'T' THEN 'ATTMD' 
                WHEN DIM_ACCT.dep_Type = 'S' THEN 'ATSAV' 
            END AS account_type,
            TO_CHAR(CAST(DIM_ACCT.ACCT_OPN_DT AS DATE), 'YYYY-MM-DD') || 'T00:00:00' AS opened,
            CASE 
                WHEN DIM_ACCT.ACCT_STS_EDW_ID = 'A' THEN 'ASACT'  
                WHEN DIM_ACCT.ACCT_STS_EDW_ID = 'C' THEN 'ASCBC' 
                WHEN DIM_ACCT.ACCT_STS_EDW_ID = 'I' THEN 'ASINA'   
                WHEN DIM_ACCT.ACCT_STS_EDW_ID = 'N' THEN 'ASNAC' 
                WHEN DIM_ACCT.ACCT_STS_EDW_ID = 'D' THEN 'ASDOR'
                ELSE 'ASOTH' 
            END AS STATUS_CODE,
        i.Dr_amt as beneficiary_comment, i.cr_amt as comments
      FROM DIM_CUST_VW DC
      LEFT JOIN DP_REPORTING_MART.TM_DM_MD_MANDATE_AUTHORIZE MA ON DC.CUST_SROGT_ID = MA.CLIENT_NO   AND CAST(MA.START_DATE AS DATE) = CURRENT_DATE - 1 
      INNER JOIN DP_SDMT_DFDN.DIM_RTAIL_BNK_ACCT_SS DIM_ACCT ON DIM_ACCT.ACCT_SROGT_ID = MA.ACCT_NO
      LEFT JOIN DP_SDMVW_DFDN.DIM_BRNCH_HIERARCHY_VW b ON DIM_ACCT.BRNCH_SROGT_ID = b.Branch_Code
      INNER JOIN RB_RELATED_ACCTS RRA ON DIM_ACCT.ACCT_SROGT_ID = RRA.ACCT_NO
      left join AMOUNT i on i.ACCT_SROGT_ID = RRA.ACCT_NO


      UNION ALL

      -- Director Client
      SELECT DISTINCT DIM_ACCT.ACCT_SROGT_ID AS ACCT_NUM, DIM_ACCT.ACCT_DESC,
          'DIRECTOR_CLIENT' AS TYP, DRC.CLIENT_NO, 'ARPYS' AS ROLE_OUTER,     dc.CUST_SROGT_ID,
          dc.mothers_name,       dc.ssn,       dc.nationality1,       dc.gender,       dc.first_name,       dc.last_name,       dc.CUST_TYPE_CD,
          dc.CUST_TYPE_DESC,       dc.to_country,       dc.CUST_NUM,       dc.birthdate,       dc.tph_contact_type,
          dc.tph_communication_type,       dc.tph_country_prefix,       dc.tph_number,       dc.address_type,
          dc.address,       dc.country_code,       dc.city,       dc.state,
          dc.institution_name,       dc.swift,       dc.institution_country,      dc.incorporation_legal_form,
            b.BRNCH_DESC AS branch, 
            COALESCE(B.CITY_NAME,B.BRNCH_DESC) AS BR_CITY_NAME, 
            b.Branch_Code AS teller,
            DIM_ACCT.ACCT_SROGT_ID AS account_, 
            DIM_ACCT.IBAN_NUM, 
            DIM_ACCT.CURY_EDW_ID AS currency_code,
            DIM_ACCT.ACCT_TITL AS account_name,
            DIM_ACCT.ACCT_TITL AS ENTITY_NAME, 
            DIM_ACCT.SRC_OF_FUND AS business, 
            CASE 
                WHEN CUST_TYPE_CD IN ('14','06','13','16','15','07','04','30','19','28','25','02','09','38','03',
                                      '05','10','01','26','21','18','12','24','20','29','22','23','08','27','31') THEN 'ARCTA'
                WHEN JOIN_ACCT_FLG = '1' THEN 'ARJTA'
                WHEN CUST_TYPE_CD = '11' THEN 'ARMRB' 
                ELSE 'ARCTA' 
            END AS Role_, 
            CASE 
                WHEN DIM_ACCT.DEP_TYPE = 'C' THEN 'ATCUR' 
                WHEN DIM_ACCT.dep_Type = 'T' THEN 'ATTMD' 
                WHEN DIM_ACCT.dep_Type = 'S' THEN 'ATSAV' 
            END AS account_type,
            TO_CHAR(CAST(DIM_ACCT.ACCT_OPN_DT AS DATE), 'YYYY-MM-DD') || 'T00:00:00' AS opened,
            CASE 
                WHEN DIM_ACCT.ACCT_STS_EDW_ID = 'A' THEN 'ASACT'  
                WHEN DIM_ACCT.ACCT_STS_EDW_ID = 'C' THEN 'ASCBC' 
                WHEN DIM_ACCT.ACCT_STS_EDW_ID = 'I' THEN 'ASINA'   
                WHEN DIM_ACCT.ACCT_STS_EDW_ID = 'N' THEN 'ASNAC' 
                WHEN DIM_ACCT.ACCT_STS_EDW_ID = 'D' THEN 'ASDOR'
                ELSE 'ASOTH' 
            END AS STATUS_CODE,
        i.Dr_amt as beneficiary_comment, i.cr_amt as comments
      FROM DIM_CUST_VW DC
      INNER JOIN DP_REPORTING_MART.FM_DIRECTOR_DTLS DRC ON DC.CUST_SROGT_ID = DRC.CLIENT_NO_DIR AND CAST(DRC.START_DATE AS DATE) = CURRENT_DATE - 1 
      INNER JOIN DP_SDMT_DFDN.DIM_RTAIL_BNK_ACCT_SS DIM_ACCT ON DIM_ACCT.CUST_SROGT_ID = DRC.CLIENT_NO
      LEFT JOIN DP_SDMVW_DFDN.DIM_BRNCH_HIERARCHY_VW b ON DIM_ACCT.BRNCH_SROGT_ID = b.Branch_Code
      INNER JOIN RB_RELATED_ACCTS RRA ON DIM_ACCT.ACCT_SROGT_ID = RRA.ACCT_NO
      left join AMOUNT i on i.ACCT_SROGT_ID = RRA.ACCT_NO

      UNION ALL

      -- Main Client
        SELECT DISTINCT  DIM_ACCT.ACCT_SROGT_ID AS ACCT_NUM, DIM_ACCT.ACCT_DESC,
          'MAIN_CLIENT' AS TYP, CAST(DC.CUST_NUM AS VARCHAR(100)) AS CLIENT_NO,
          CAST('' AS VARCHAR(100)) AS ROLE_OUTER,    dc.CUST_SROGT_ID,
          dc.mothers_name,       dc.ssn,       dc.nationality1,       dc.gender,       dc.first_name,       dc.last_name,       dc.CUST_TYPE_CD,
          dc.CUST_TYPE_DESC,       dc.to_country,       dc.CUST_NUM,       dc.birthdate,       dc.tph_contact_type,
          dc.tph_communication_type,       dc.tph_country_prefix,       dc.tph_number,       dc.address_type,
          dc.address,       dc.country_code,       dc.city,       dc.state,
          dc.institution_name,       dc.swift,       dc.institution_country,      dc.incorporation_legal_form,
            b.BRNCH_DESC AS branch, 
            COALESCE(B.CITY_NAME,B.BRNCH_DESC) AS BR_CITY_NAME, 
            b.Branch_Code AS teller,
            DIM_ACCT.ACCT_SROGT_ID AS account_, 
            DIM_ACCT.IBAN_NUM, 
            DIM_ACCT.CURY_EDW_ID AS currency_code,
            DIM_ACCT.ACCT_TITL AS account_name,
            DIM_ACCT.ACCT_TITL AS ENTITY_NAME, 
            DIM_ACCT.SRC_OF_FUND AS business, 
            CASE 
                WHEN CUST_TYPE_CD IN ('14','06','13','16','15','07','04','30','19','28','25','02','09','38','03',
                                      '05','10','01','26','21','18','12','24','20','29','22','23','08','27','31') THEN 'ARCTA'
                WHEN JOIN_ACCT_FLG = '1' THEN 'ARJTA'
                WHEN CUST_TYPE_CD = '11' THEN 'ARMRB' 
                ELSE 'ARCTA' 
            END AS Role_, 
            CASE 
                WHEN DIM_ACCT.DEP_TYPE = 'C' THEN 'ATCUR' 
                WHEN DIM_ACCT.dep_Type = 'T' THEN 'ATTMD' 
                WHEN DIM_ACCT.dep_Type = 'S' THEN 'ATSAV' 
            END AS account_type,
            TO_CHAR(CAST(DIM_ACCT.ACCT_OPN_DT AS DATE), 'YYYY-MM-DD') || 'T00:00:00' AS opened,
            CASE 
                WHEN DIM_ACCT.ACCT_STS_EDW_ID = 'A' THEN 'ASACT'  
                WHEN DIM_ACCT.ACCT_STS_EDW_ID = 'C' THEN 'ASCBC' 
                WHEN DIM_ACCT.ACCT_STS_EDW_ID = 'I' THEN 'ASINA'   
                WHEN DIM_ACCT.ACCT_STS_EDW_ID = 'N' THEN 'ASNAC' 
                WHEN DIM_ACCT.ACCT_STS_EDW_ID = 'D' THEN 'ASDOR'
                ELSE 'ASOTH' 
            END AS STATUS_CODE,
        i.Dr_amt as beneficiary_comment, i.cr_amt as comments
        FROM DIM_CUST_VW DC
        INNER JOIN DP_SDMT_DFDN.DIM_RTAIL_BNK_ACCT_SS DIM_ACCT ON DIM_ACCT.CUST_SROGT_ID = DC.CUST_SROGT_ID
        LEFT JOIN DP_SDMVW_DFDN.DIM_BRNCH_HIERARCHY_VW b ON DIM_ACCT.BRNCH_SROGT_ID = b.Branch_Code
        INNER JOIN RB_RELATED_ACCTS RRA ON DIM_ACCT.ACCT_SROGT_ID = RRA.ACCT_NO
        left join AMOUNT i on i.ACCT_SROGT_ID = RRA.ACCT_NO




    """
