import json



def get_cash_deposit_query(trxn_date, entity_individual_flag):
	query = rf"""WITH ENTITY AS (
		SELECT
		FCT.TSACTN_ID,
		FCT.ACCT_SROGT_ID
		FROM DP_SDMVW_DFDN.FCT_RTAIL_BNK_TSACTN_VW FCT
		INNER JOIN DP_SDMVW_DFDN.DIM_RTAIL_BNK_ACCT_VW ACCT ON ACCT.ACCT_SROGT_ID = FCT.ACCT_SROGT_ID
		LEFT JOIN (select CURY_EDW_ID, EXCH_RATE as CCY_RATE FROM  DP_SDMVW_DFDN.FCT_CURY_EXCH_RATE_VW where BATCH_DT = '{trxn_date}') EXC
		ON FCT.CURY_EDW_ID = EXC.CURY_EDW_ID
		WHERE 1=1
		--AND FCT.TSACTN_ID IN ('6576257638')
		AND FCT.TSACTN_TYPE_EDW_ID IN ('0001','0201','0006')
		AND FCT.TSACTN_DT BETWEEN '{trxn_date}' AND '{trxn_date}'
		AND CASE WHEN EXC.CURY_EDW_ID IS NOT NULL THEN FCT.TSACTN_AMT * CCY_RATE ELSE FCT.TSACTN_AMT END >= '2000000'
		AND 
		( 
		ACCT.CUST_TYPE_EDW_ID IN ( '63','51','36','31','61','34','53','37','35','65','33','32','55','62','64','54','52') 
		OR
		EXISTS(
		SELECT 1 FROM DP_SDMVW_DFDN.DIM_CTR_Keywords_VW t 
		WHERE t.flag = 'NO' AND ACCT.ACCT_TITL LIKE '%' || t.keyword || '%'
		)
		OR 
		EXISTS(
		SELECT 1 FROM DP_SDMVW_DFDN.DIM_CTR_Keywords_VW t 
		WHERE t.flag = 'YES' AND REGEXP_INSTR(ACCT.ACCT_TITL, '(^|[^A-Z0-9])' || t.keyword || '([^A-Z0-9]|$)', 1,1,0, 'i') > 0
		)
		)
		AND FCT.CR_DR_IND = 'C'
		AND FCT.RVSL_SEQ_NUM IS NULL
		AND FCT.Reveral_IND = 'N'
		AND FCT.TRAC_ID IS NULL
		)

		,TRXNS AS (
		SELECT
		FCT.*, 
		CASE WHEN FCT.CURY_EDW_ID <> 'PKR' THEN FCT.CURY_EDW_ID ELSE CAST(NULL AS VARCHAR(10)) END AS FRGN_CCY,
		CASE WHEN FCT.CURY_EDW_ID <> 'PKR' THEN CAST(FCT.TSACTN_AMT AS INT) ELSE CAST(NULL AS VARCHAR(10)) END AS FRGN_TSACTN_AMT,
		CASE WHEN FCT.CURY_EDW_ID <> 'PKR' THEN EXC.CCY_RATE ELSE CAST(NULL AS VARCHAR(10)) END AS EXCHANGE_RATE,
		FCT.TSACTN_AMT * EXC.CCY_RATE AS FRGN_TSACTN_AMT_PKR,
		ACCT.ACCT_TITL,
		ACCT.ACCT_SROGT_ID AS ACCOUNT_SROGT_ID, ACCT.CUST_TYPE_EDW_ID AS ACCOUNT_CUST_TYPE_EDW_ID , ACCT.BRNCH_SROGT_ID AS ACCT_BRNCH_SROGT_ID ,
		ACCT.ACCT_ORIGNL_OPN_DT , ACCT.ACCT_DESC, ACCT.CURY_EDW_ID AS ACCT_CURY_EDW_ID,
		PROD.ACCT_TYPE_DESC,
		--PROD.CODE AS ACCT_TYPE_CODE ,
		CASE WHEN REGEXP_SIMILAR(UPPER(ACCT.ACCT_TITL), '.*(^|[^A-Z0-9])CDC([^A-Z0-9]|$).*') = 1 THEN 'ATSAV' ELSE PROD.CODE END AS ACCT_TYPE_CODE,
		COD.CATEGORY_TYPE_DESC,
		COD.CODE AS CATEGORY_TYPE_CODE,
		CASE WHEN E.ACCT_SROGT_ID IS NOT NULL THEN 'ENTITY' ELSE 'INDIVIDUAL' END AS CATEGORY
		
		FROM DP_SDMVW_DFDN.FCT_RTAIL_BNK_TSACTN_VW FCT
		INNER JOIN DP_SDMVW_DFDN.DIM_RTAIL_BNK_ACCT_VW ACCT ON ACCT.ACCT_SROGT_ID = FCT.ACCT_SROGT_ID
		LEFT JOIN ENTITY E ON FCT.TSACTN_ID = E.TSACTN_ID 
		LEFT JOIN DP_SDMT_DFDN.DIM_CTR_ACCT_TYPE prod ON ACCT.PROD_SROGT_ID = prod.ACCT_TYPE 
		LEFT JOIN DP_SDMT_DFDN.DIM_CTR_CATEGORY_CODES COD ON ACCT.CUST_TYPE_EDW_ID = COD.CATEGORY_TYPE
		LEFT JOIN (select CURY_EDW_ID, EXCH_RATE as CCY_RATE FROM  DP_SDMVW_DFDN.FCT_CURY_EXCH_RATE_VW where BATCH_DT = '{trxn_date}') EXC
		ON FCT.CURY_EDW_ID = EXC.CURY_EDW_ID
		WHERE 1=1
		--AND FCT.TSACTN_ID IN ('6576257638')
		AND FCT.TSACTN_TYPE_EDW_ID IN ('0001','0201','0006')
		AND FCT.TSACTN_DT BETWEEN '{trxn_date}' AND '{trxn_date}'
		AND CASE WHEN EXC.CURY_EDW_ID IS NOT NULL THEN FCT.TSACTN_AMT * CCY_RATE ELSE FCT.TSACTN_AMT END >= '2000000'
		AND FCT.CR_DR_IND = 'C'
		AND FCT.RVSL_SEQ_NUM IS NULL
		AND FCT.Reveral_IND = 'N'
		AND FCT.TRAC_ID IS NULL
		)
		
		-- DP_REPORTING_MART.TM_DM_MD_MANDATE_AUTHORIZE
		, MANDATE AS (
		SELECT x.*,
	    ROW_NUMBER() OVER(PARTITION BY ACCT_SROGT_ID ORDER BY M_DT_OF_BIRTH DESC) AS M_RN
	    FROM (
			SELECT
			    T.ACCT_SROGT_ID,
			    T.TSACTN_ID,
			    M.CLIENT_NO AS M_CLIENT_NO,
				'TRUE' AS M_IS_PRIMARY, 
				CASE 
					 WHEN MC.GNDR IS NOT NULL THEN MC.GNDR
					 WHEN MC.GNDR IS NULL THEN 
								CASE WHEN RIGHT(MC.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(MC.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'M' 
								WHEN RIGHT(MC.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(MC.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'F' 
								ELSE CAST(NULL AS VARCHAR(10)) END END AS M_GNDR,			
				CASE 
					 WHEN MC.TITL IS NOT NULL THEN MC.TITL
					 WHEN MC.TITL IS NULL THEN 
								CASE WHEN RIGHT(MC.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(MC.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'MR' 
								WHEN RIGHT(MC.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(MC.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'MS'
								ELSE CAST(NULL AS VARCHAR(10)) END END AS M_TITL, 			

			    TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
						FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) )  AS  M_FRST_NAME,
				
				CASE WHEN  REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0 
							THEN  TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
				              			  POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) )
							ELSE 
									CASE WHEN (MC.FRST_NAME IS NULL AND MC.MDL_NAME IS NULL AND MC.LAST_NAME IS NULL) OR (MC.FRST_NAME = '' AND MC.MDL_NAME = '' AND MC.LAST_NAME = '')
												THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
												 			FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
												ELSE 
														CASE WHEN REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(MC.FRST_NAME, '') || ' ' || COALESCE(MC.MDL_NAME, '') || ' ' || COALESCE(MC.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0
																	THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(MC.FRST_NAME, '') || ' ' || COALESCE(MC.MDL_NAME, '') || ' ' || COALESCE(MC.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
													            				POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(MC.FRST_NAME, '') || ' ' || COALESCE(MC.MDL_NAME, '') || ' ' || COALESCE(MC.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) 
														ELSE TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
																 	FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
														END
									END
				END	AS M_LAST_NAME ,
				
			    TO_CHAR(MC.DT_OF_BIRTH , 'YYYY-MM-DD') ||  'T00:00:00' AS M_DT_OF_BIRTH,
				TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.FTHR_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) AS M_MOTHER_NAME,
				
				MC.IDNTFTN_TYPE_EDW_ID AS M_SSN_TYPE,
				CASE WHEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) = '' THEN CAST(NULL AS VARCHAR(10)) 
							   ELSE TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) END AS M_SSN,
			     CASE
					when MC.MBL_NUM is not null AND MC.MBL_NUM <> ''  
					THEN CASE WHEN REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(MC.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' ) IS NULL OR REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(MC.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' ) = ''
								THEN TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(MC.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') ) ELSE REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(MC.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' )  END
			        when MC.PHN_RSDNC is not null AND MC.PHN_RSDNC <> '' then TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(MC.PHN_RSDNC), '[^ ]+', 1, 1), '[^0-9]', '') )
			        else 
					case 
						WHEN REGEXP_SIMILAR(MC.PHN_BUSN, '.*[A-Za-z].*') = '1' AND REGEXP_SIMILAR(MC.PHN_BUSN, '.*[0-9].*') = '1' THEN CAST(NULL AS VARCHAR(11))
						WHEN REGEXP_SIMILAR(MC.PHN_BUSN, '.*[A-Za-z].*') = '1' THEN CAST(NULL AS VARCHAR(11))
						ELSE 
							case
								when substr(regexp_replace(MC.PHN_BUSN, '[^0-9]', ''), 1,3) = '092' then substr(regexp_replace(MC.PHN_BUSN, '[^0-9]', ''), 3) 
								when substr(regexp_replace(MC.PHN_BUSN, '[^0-9]', ''), 1,2) = '92' then substr(regexp_replace(MC.PHN_BUSN, '[^0-9]', ''), 3)  
								ELSE trim(LEADING '0' FROM regexp_replace(MC.PHN_BUSN, '[^0-9]', ''))
							end
					end 
				END as M_tph_number,      	
				
				TRIM(OREPLACE(OREPLACE(
				CASE 
				WHEN TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is not null AND TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3
				              THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' ')  , '[[:space:]]+', ' '))  
				WHEN (TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
						       AND (TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
						      THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' ')) 
				WHEN (TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
						       AND ( TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(MC.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))
				WHEN (TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3 ) 
						       AND (TRIM(REGEXP_REPLACE(TRIM(MC.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(MC.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.OTH_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(MC.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))		   
				ELSE CAST(NULL AS VARCHAR(10)) 
				END
				,CHR(13),' '),CHR(10), ' ')) as M_address,

			    CASE WHEN _MDO.OCPTN_DESC IS NOT NULL OR _MDO.OCPTN_DESC <> '' THEN _MDO.OCPTN_DESC ELSE 'Others' END AS M_OCCUPATION,
				
				MC.CTRY_OF_NTLTY as M_nationality1,
				'PK' as M_Residence,
				CASE WHEN MC.MBL_NUM is not null AND MC.MBL_NUM <> '' then 'PAPVT' when MC.MBL_NUM is null OR MC.MBL_NUM = '' then 'PAOFF' END as M_tph_contact_type,
				CASE WHEN MC.MBL_NUM is not null AND MC.MBL_NUM <> '' then 'COMOB' else 'COLAN' END as M_tph_communication_type,
				'92' as M_tph_country_prefix,
				
				CASE WHEN MC.PERM_ADDR is not null and MC.PERM_ADDR <> '' then 'PAPVT' 
							when MC.PERM_ADDR is null OR MC.PERM_ADDR = '' then 'PAOFF' END as M_address_type,
							
				CASE WHEN TRIM(MC.RSDNTL_CITY)  = '0' THEN CAST(NULL AS VARCHAR(10)) ELSE MC.RSDNTL_CITY END AS M_city, 
				
				'PK' as M_country_code,
				CASE  
				when substr(MC.IDNTFTN_VAL,1,1) IN ('1', '2') then 'KHYBER-PAKHTUNKHWA'
				when substr(MC.IDNTFTN_VAL,1,1) IN ('3', '6') then 'PUNJAB'
				when substr(MC.IDNTFTN_VAL,1,1) = '4' then 'SINDH'
				when substr(MC.IDNTFTN_VAL,1,1) = '5' then 'BALOCHISTAN'
				when substr(MC.IDNTFTN_VAL,1,1) = '7' then 'GILGIT-BALISTAN'
				when substr(MC.IDNTFTN_VAL,1,1) = '8' then 'AZAD-KASHMIR'
				ELSE cast(null as varchar(10)) 
				END as M_state,
				
				'ARPYS' AS M_role
				
			    ,ROW_NUMBER() OVER(PARTITION BY M.CLIENT_NO ORDER BY M.CLIENT_NO) AS RN
		    FROM  TRXNS T
		    INNER JOIN DP_REPORTING_MART.TM_DM_MD_MANDATE_AUTHORIZE M ON T.ACCT_SROGT_ID = M.ACCT_NO  -- DP_SDMVW_DFDN.TM_DM_MD_MANDATE_AUTHORIZE_VW 
		    LEFT JOIN DP_SDMVW_DFDN.DIM_CUST_VW MC ON MC.CUST_SROGT_ID = M.CLIENT_NO AND MC.SYSTEM_CODE = 'CBS'
		    LEFT JOIN DP_SDMT_DFDN.DIM_OCPTN_SS _MDO ON MC.OCPTN_EDW_ID = _MDO.OCPTN_EDW_ID
		    WHERE 1=1 AND M.START_DATE = (SELECT CAST(MAX(START_DATE) AS DATE) AS START_DATE FROM DP_REPORTING_MART.TM_DM_MD_MANDATE_AUTHORIZE)
			 -- CAST(CURRENT_DATE - 1 AS DATE)
			
	    ) AS X
	    WHERE 1=1
	  	AND X.RN = 1
		)
		
		                             
		-- DP_REPORTING_MART.FM_DIRECTOR_DTLS
		, DIRECTORS AS (
		SELECT x.*, ROW_NUMBER() OVER(PARTITION BY CUST_SROGT_ID ORDER BY D_DT_OF_BIRTH DESC) AS D_RN
		FROM (
			SELECT 
				T.ACCT_SROGT_ID,
				T.CUST_SROGT_ID,
				T.TSACTN_ID,
				DC.CUST_SROGT_ID AS D_CUST_SROGT_ID,
				
				CASE 
					 WHEN DC.GNDR IS NOT NULL THEN DC.GNDR
					 WHEN DC.GNDR IS NULL THEN 
								CASE WHEN RIGHT(DC.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(DC.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'M' 
								WHEN RIGHT(DC.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(DC.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'F' 
								ELSE CAST(NULL AS VARCHAR(10)) END END AS D_GNDR,			
				CASE 
					 WHEN DC.TITL IS NOT NULL THEN DC.TITL
					 WHEN DC.TITL IS NULL THEN 
								CASE WHEN RIGHT(DC.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(DC.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'MR' 
								WHEN RIGHT(DC.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(DC.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'MS'
								ELSE CAST(NULL AS VARCHAR(10)) END END AS D_TITL, 	

				TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
						FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) )  AS  D_FRST_NAME,
				
				CASE WHEN  REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0 
							THEN  TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
				              			  POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) )
							ELSE 
									CASE WHEN (DC.FRST_NAME IS NULL AND DC.MDL_NAME IS NULL AND DC.LAST_NAME IS NULL) OR (DC.FRST_NAME = '' AND DC.MDL_NAME = '' AND DC.LAST_NAME = '')
												THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
												 			FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
												ELSE 
														CASE WHEN REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(DC.FRST_NAME, '') || ' ' || COALESCE(DC.MDL_NAME, '') || ' ' || COALESCE(DC.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0
																	THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(DC.FRST_NAME, '') || ' ' || COALESCE(DC.MDL_NAME, '') || ' ' || COALESCE(DC.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
													            				POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(DC.FRST_NAME, '') || ' ' || COALESCE(DC.MDL_NAME, '') || ' ' || COALESCE(DC.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) 
														ELSE TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
																 	FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
														END
									END
				END	AS D_LAST_NAME ,
				
				TO_CHAR(DC.DT_OF_BIRTH , 'YYYY-MM-DD') ||  'T00:00:00' AS D_DT_OF_BIRTH,
				TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.FTHR_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) AS D_MOTHER_NAME,
				
				DC.IDNTFTN_TYPE_EDW_ID AS D_SSN_TYPE,
				CASE WHEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) = '' THEN CAST(NULL AS VARCHAR(10)) 
							   ELSE TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) END AS D_SSN,
				 CASE
					when DC.MBL_NUM is not null AND DC.MBL_NUM <> ''  
					THEN CASE WHEN REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(DC.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' ) IS NULL OR REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(DC.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' ) = ''
								THEN TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(DC.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') ) ELSE REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(DC.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' )  END
			        when DC.PHN_RSDNC is not null AND DC.PHN_RSDNC <> '' then TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(DC.PHN_RSDNC), '[^ ]+', 1, 1), '[^0-9]', '') )
			        else 
					case 
						WHEN REGEXP_SIMILAR(DC.PHN_BUSN, '.*[A-Za-z].*') = '1' AND REGEXP_SIMILAR(DC.PHN_BUSN, '.*[0-9].*') = '1' THEN CAST(NULL AS VARCHAR(11))
						WHEN REGEXP_SIMILAR(DC.PHN_BUSN, '.*[A-Za-z].*') = '1' THEN CAST(NULL AS VARCHAR(11))
						ELSE 
							case
								when substr(regexp_replace(DC.PHN_BUSN, '[^0-9]', ''), 1,3) = '092' then substr(regexp_replace(DC.PHN_BUSN, '[^0-9]', ''), 3) 
								when substr(regexp_replace(DC.PHN_BUSN, '[^0-9]', ''), 1,2) = '92' then substr(regexp_replace(DC.PHN_BUSN, '[^0-9]', ''), 3)  
								ELSE trim(LEADING '0' FROM regexp_replace(DC.PHN_BUSN, '[^0-9]', ''))
							end
					end 
				END as D_tph_number, 	
				
				TRIM(OREPLACE(OREPLACE(
				CASE 
				WHEN TRIM(REGEXP_REPLACE(TRIM(DC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is not null AND TRIM(REGEXP_REPLACE(TRIM(DC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(DC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3
				              THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(DC.PERM_ADDR), '[^A-Za-z0-9 ]', ' ')  , '[[:space:]]+', ' '))  
				WHEN (TRIM(REGEXP_REPLACE(TRIM(DC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(DC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(DC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
						       AND (TRIM(REGEXP_REPLACE(TRIM(DC.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(DC.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(DC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
						      THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(DC.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' ')) 
				WHEN (TRIM(REGEXP_REPLACE(TRIM(DC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(DC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(DC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
						       AND ( TRIM(REGEXP_REPLACE(TRIM(DC.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(DC.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(DC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(DC.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))
				WHEN (TRIM(REGEXP_REPLACE(TRIM(DC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(DC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(DC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3 ) 
						       AND (TRIM(REGEXP_REPLACE(TRIM(DC.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(DC.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(DC.OTH_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(DC.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))		   
				ELSE CAST(NULL AS VARCHAR(10)) 
				END
				,CHR(13),' '),CHR(10), ' ')) as D_address,	

				CASE WHEN _DDO.OCPTN_DESC IS NOT NULL OR _DDO.OCPTN_DESC <> '' THEN _DDO.OCPTN_DESC ELSE 'Others' END AS D_OCCUPATION,
				
				DC.CTRY_OF_NTLTY as D_nationality1,
				'PK' as D_Residence,
				CASE WHEN DC.MBL_NUM is not null AND DC.MBL_NUM <> '' then 'PAPVT' when DC.MBL_NUM is null OR DC.MBL_NUM = '' then 'PAOFF' END as D_tph_contact_type,
				CASE WHEN DC.MBL_NUM is not null AND DC.MBL_NUM <> '' then 'COMOB' else 'COLAN' END as D_tph_communication_type,
				'92' as D_tph_country_prefix,
				
				CASE WHEN DC.PERM_ADDR is not null and DC.PERM_ADDR <> '' then 'PAPVT' 
						    when DC.PERM_ADDR is null OR DC.PERM_ADDR = '' then 'PAOFF' END as D_address_type,
							
				CASE WHEN TRIM(DC.RSDNTL_CITY) = '0' THEN CAST(NULL AS VARCHAR(10)) ELSE DC.RSDNTL_CITY END AS D_city, 
				
				'PK' as D_country_code,
				CASE  
				when substr(DC.IDNTFTN_VAL,1,1) IN ('1', '2') then 'KHYBER-PAKHTUNKHWA'
				when substr(DC.IDNTFTN_VAL,1,1) IN ('3', '6') then 'PUNJAB'
				when substr(DC.IDNTFTN_VAL,1,1) = '4' then 'SINDH'
				when substr(DC.IDNTFTN_VAL,1,1) = '5' then 'BALOCHISTAN'
				when substr(DC.IDNTFTN_VAL,1,1) = '7' then 'GILGIT-BALISTAN'
				when substr(DC.IDNTFTN_VAL,1,1) = '8' then 'AZAD-KASHMIR'
				ELSE cast(null as varchar(10)) 
				END as D_state,
				
				'ERDIR' AS D_role
				
				,ROW_NUMBER() OVER(PARTITION BY DD.CLIENT_NO_DIR ORDER BY DD.CLIENT_NO_DIR) AS RN
			FROM TRXNS T
			INNER JOIN DP_REPORTING_MART.FM_DIRECTOR_DTLS DD ON T.CUST_SROGT_ID = DD.CLIENT_NO  -- DP_SDMVW_DFDN.FM_DIRECTOR_DTLS_VW 
			LEFT JOIN DP_SDMVW_DFDN.DIM_CUST_VW DC ON DC.CUST_SROGT_ID = DD.CLIENT_NO_DIR AND DC.SYSTEM_CODE = 'CBS' 
			LEFT JOIN DP_SDMT_DFDN.DIM_OCPTN_SS _DDO ON DC.OCPTN_EDW_ID = _DDO.OCPTN_EDW_ID
			WHERE 1=1 AND DD.START_DATE = (SELECT CAST(MAX(START_DATE) AS DATE) AS START_DATE FROM DP_REPORTING_MART.FM_DIRECTOR_DTLS)
			-- CAST(CURRENT_DATE - 1 AS DATE)
		) X 
		WHERE 1=1 
		AND X.RN = 1
		)
					
		, WALKIN_DETAILS AS (
		
		SELECT * FROM (
			select 
			w.Transaction_ID,
			CASE 
			 WHEN w.Cust_Type = 'AH' AND d.GNDR IS NOT NULL THEN d.GNDR
			 WHEN w.Cust_Type = 'AH' AND d.GNDR IS NULL THEN 
						CASE WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'M' 
						WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'F' 
						ELSE CAST(NULL AS VARCHAR(10)) END 
			 WHEN w.Cust_Type = 'TP' THEN
						CASE WHEN RIGHT(W_CNIC,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(W_CNIC, '-', ''), '/', '')) = 13 THEN 'M' 
						WHEN RIGHT(W_CNIC,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(W_CNIC, '-', ''), '/', '')) = 13  THEN 'F' 
						ELSE CAST(NULL AS VARCHAR(10)) END  
			END as TFMC_Gender,

			CASE 
			 WHEN w.Cust_Type = 'AH' AND d.TITL IS NOT NULL THEN d.TITL
			 WHEN w.Cust_Type = 'AH' AND d.TITL IS NULL THEN 
						CASE WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'MR' 
						WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'MS'
						END 
			 WHEN w.Cust_Type = 'TP' THEN
						CASE WHEN RIGHT(W_CNIC,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(W_CNIC, '-', ''), '/', '')) = 13 THEN 'MR' 
						WHEN RIGHT(W_CNIC,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(W_CNIC, '-', ''), '/', '')) = 13  THEN 'MS' 
						ELSE CAST(NULL AS VARCHAR(10)) END  
			END as TFMC_Title,
			CASE 
			WHEN w.Cust_Type = 'AH'  THEN
			TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
							FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
			WHEN w.Cust_Type = 'TP'  THEN
			TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
							FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) )  
			END AS TFMC_First_Name ,

			CASE 
			WHEN w.Cust_Type = 'AH'  THEN
				CASE WHEN  REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0 
							THEN  TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
				              			  POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) )
							ELSE 
									CASE WHEN (D.FRST_NAME IS NULL AND D.MDL_NAME IS NULL AND D.LAST_NAME IS NULL) OR (D.FRST_NAME = '' AND D.MDL_NAME = '' AND D.LAST_NAME = '')
												THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
												 			FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
												ELSE 
														CASE WHEN REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0
																	THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
													            				POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) 
														ELSE TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
																 	FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
														END
									END
				END
			WHEN w.Cust_Type = 'TP'  THEN 
				CASE  		
						 WHEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
								POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) IS NULL 
								OR 
						TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
								POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) = '' 
						THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
								FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) )
						ELSE TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
								POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) END
			END AS TFMC_Last_Name ,
			CASE WHEN w.Cust_Type = 'AH'  THEN TO_CHAR(d.DT_OF_BIRTH , 'YYYY-MM-DD') ||  'T00:00:00'  WHEN w.Cust_Type = 'TP' THEN TO_CHAR(w.BIRTH_DATE  , 'YYYY-MM-DD') ||  'T00:00:00'  END as TFMC_Birth_Date,
			CASE WHEN w.Cust_Type = 'AH'  THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(d.FTHR_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) 
						 WHEN w.Cust_Type = 'TP' THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w.FATHER_NAME , '[^A-Za-z ]', ' '), ' +', ' ')) END as TFMC_Mother_Name,

			CASE WHEN w.Cust_Type = 'AH'  THEN D.IDNTFTN_TYPE_EDW_ID WHEN w.Cust_Type = 'TP' THEN 
						CASE WHEN LENGTH(REGEXP_REPLACE(w.w_cnic, '[^0-9]', '')) = 13 THEN 'NIC' 
									 WHEN REGEXP_SIMILAR( TRIM(REGEXP_REPLACE(w.w_cnic, '[^A-Za-z0-9]', '')), '^[A-Za-z0-9]+$') = 1 THEN 'PPT'  
									 ELSE CAST(NULL AS VARCHAR(10)) END
			END AS TFMC_ssn_type,
			CASE WHEN w.Cust_Type = 'AH'  THEN d.IDNTFTN_VAL WHEN w.Cust_Type = 'TP' THEN w.w_cnic END as TFMC_ssn,
			CASE WHEN w.Cust_Type = 'AH'  THEN d.CTRY_OF_NTLTY WHEN w.Cust_Type = 'TP' THEN 'PK' END as TFMC_nationality1,
			'PK' as TFMC_Residence,

			CASE WHEN w.Cust_Type = 'AH'  THEN case when d.MBL_NUM is not null AND d.MBL_NUM <> '' then 'PAPVT' when d.MBL_NUM is null OR d.MBL_NUM = '' then 'PAOFF' end
			WHEN w.Cust_Type = 'TP' THEN  'PAPVT' END as TFMC_tph_contact_type,

			CASE WHEN w.Cust_Type = 'AH'  
			THEN case when d.MBL_NUM is not null AND d.MBL_NUM <> '' then 'COMOB' else 'COLAN' end
			WHEN w.Cust_Type = 'TP' THEN  'COMOB' END as TFMC_tph_communication_type,

			'92' as TFMC_tph_country_prefix,
						
			CASE WHEN w.Cust_Type = 'AH'  THEN				  
			CASE
				when D.MBL_NUM is not null AND D.MBL_NUM <> ''  
				THEN CASE WHEN REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' ) IS NULL OR REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' ) = ''
							THEN TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') ) ELSE REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' )  END
		        when D.PHN_RSDNC is not null AND D.PHN_RSDNC <> '' then TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.PHN_RSDNC), '[^ ]+', 1, 1), '[^0-9]', '') )
		        else 
				case 
					WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' AND REGEXP_SIMILAR(D.PHN_BUSN, '.*[0-9].*') = '1' THEN CAST(NULL AS VARCHAR(11))
					WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' THEN CAST(NULL AS VARCHAR(11))
					ELSE 
						case
							when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,3) = '092' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3) 
							when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,2) = '92' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3)  
							ELSE trim(LEADING '0' FROM regexp_replace(D.PHN_BUSN, '[^0-9]', ''))
						end
				end 
			END		    
			WHEN w.Cust_Type = 'TP' THEN  TRIM(LEADING '0' FROM w.CONTACT_NO) END as TFMC_tph_number,

			CASE WHEN w.Cust_Type = 'AH'  THEN	
			CASE WHEN D.PERM_ADDR is not null and D.PERM_ADDR <> '' then 'PAPVT' 
						when D.PERM_ADDR is null OR D.PERM_ADDR = '' then 'PAOFF' END
			WHEN w.Cust_Type = 'TP' THEN  'PAPVT' END as TFMC_address_type,

			TRIM(OREPLACE(OREPLACE( 	
			CASE WHEN w.Cust_Type = 'AH'  THEN	
					CASE 
					WHEN TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is not null AND TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3
					              THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' ')  , '[[:space:]]+', ' '))  
					WHEN (TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
							       AND (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							      THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' ')) 
					WHEN (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
							       AND ( TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
								   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))
					WHEN (TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3 ) 
							       AND (TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
								   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))		   
					ELSE CAST(NULL AS VARCHAR(10)) 
					END
			WHEN w.Cust_Type = 'TP' THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(w.CUSTOMER_ADDRESS), '[^A-Za-z0-9 ]', ' ')  , '[[:space:]]+', ' ')) END ,CHR(13),' '),CHR(10), ' ')) as TFMC_address,

			--CASE WHEN w.Cust_Type = 'AH'  THEN	CASE WHEN REGEXP_REPLACE(TRIM(d.RSDNTL_CITY), '[^A-Za-z ]', '') = '' THEN CAST(NULL AS VARCHAR(10)) ELSE REGEXP_REPLACE(TRIM(d.RSDNTL_CITY), '[^A-Za-z ]', '') END
			--WHEN w.Cust_Type = 'TP' THEN CAST(NULL	AS VARCHAR(10)) END as TFMC_city,

			B.CITY_NAME AS TFMC_city, 
			
			'PK' as TFMC_country_code,
			CASE WHEN w.Cust_Type = 'AH'  THEN
			case 
			when substr(d.IDNTFTN_VAL,1,1) IN ('1', '2') then 'KHYBER-PAKHTUNKHWA'
			when substr(d.IDNTFTN_VAL,1,1) IN ('3', '6') then 'PUNJAB'
			when substr(d.IDNTFTN_VAL,1,1) = '4' then 'SINDH'
			when substr(d.IDNTFTN_VAL,1,1) = '5' then 'BALOCHISTAN'
			when substr(d.IDNTFTN_VAL,1,1) = '7' then 'GILGIT-BALISTAN'
			when substr(d.IDNTFTN_VAL,1,1) = '8' then 'AZAD-KASHMIR'
			ELSE cast(null as varchar(10)) 
			end
			WHEN w.Cust_Type = 'TP' THEN  
			case 
			when substr(W.W_CNIC,1,1) IN ('1', '2') then 'KHYBER-PAKHTUNKHWA'
			when substr(W.W_CNIC,1,1) IN ('3', '6') then 'PUNJAB'
			when substr(W.W_CNIC,1,1) = '4' then 'SINDH'
			when substr(W.W_CNIC,1,1) = '5' then 'BALOCHISTAN'
			when substr(W.W_CNIC,1,1) = '7' then 'GILGIT-BALISTAN'
			when substr(W.W_CNIC,1,1) = '8' then 'AZAD-KASHMIR'
			ELSE cast(null as varchar(10)) 
			end
			END as TFMC_state,

			CASE WHEN w.Cust_Type = 'AH'  THEN CASE WHEN O.OCPTN_DESC IS NOT NULL OR O.OCPTN_DESC <> '' THEN O.OCPTN_DESC ELSE 'Others' END
			WHEN w.Cust_Type = 'TP' THEN W.w_source_of_funds END AS TFMC_occupation,
			'PK' as TFMC_from_country,
			
			DENSE_RANK() OVER(PARTITION BY d.IDNTFTN_VAL ORDER BY d.START_DATE DESC) AS RN
			
			FROM TRXNS T
			INNER JOIN dp_sdmt_dfdn.WALKIN_TXN W on T.tsactn_id = w.Transaction_ID 
			LEFT JOIN DP_SDMVW_DFDN.DIM_CUST_VW d ON d.IDNTFTN_VAL = w.w_cnic and d.system_code = 'CBS'
			LEFT JOIN DP_SDMT_DFDN.DIM_OCPTN_SS O ON O.OCPTN_EDW_ID = D.OCPTN_EDW_ID  and d.system_code = 'CBS'
			LEFT JOIN DP_SDMVW_DFDN.DIM_BRNCH_HIERARCHY_VW B ON T.BRNCH_SROGT_ID = B.BRNCH_SROGT_ID
			WHERE 1=1
			) X
		WHERE 1=1 
		AND X.RN = 1
		AND X.TFMC_ssn_type NOT IN ('BFN', 'FXP')
		)
		
		, Final_Chunk AS (
		SELECT 
		T.CATEGORY,
		T.CATEGORY_TYPE_DESC,
		TRIM(T.TSACTN_ID) AS transactionnumber,
		B.BRNCH_DESC || ' (' || T.BRNCH_SROGT_ID || ')' AS transaction_location,
		CASE 
		WHEN CR_DR_IND = 'D' THEN 'CHEQUE WITHDRAWAL'  
		WHEN CR_DR_IND = 'C' THEN 'CASH DEPOSIT' 
		END AS transaction_description,
		TO_CHAR(T.TSACTN_DT , 'YYYY-MM-DD') ||  'T00:00:00' as date_transaction,
		B.BRNCH_DESC || ' (' || T.BRNCH_SROGT_ID || ')' AS teller,
		B.CITY_NAME AS authorized,
		'TMBRN' AS transmode_code,
		CASE WHEN T.CURY_EDW_ID = 'PKR' THEN CAST(T.TSACTN_AMT AS INT)
		ELSE CAST(T.FRGN_TSACTN_AMT_PKR AS INT) END AS amount_local,   
		CASE 
		WHEN CR_DR_IND = 'D' THEN 'FTCHQ'  
		WHEN CR_DR_IND = 'C' THEN 'FTCAS'
		END AS TFMC_from_funds_code,
		W.TFMC_Gender,
		W.TFMC_Title,
		W.TFMC_First_Name,
		W.TFMC_Last_Name,
		W.TFMC_Birth_Date,
		W.TFMC_Mother_Name,
		W.TFMC_ssn_type,
		W.TFMC_ssn,
		W.TFMC_nationality1,
		W.TFMC_Residence,
		W.TFMC_tph_contact_type,
		W.TFMC_tph_communication_type,
		W.TFMC_tph_country_prefix,
		W.TFMC_tph_number,
		W.TFMC_address_type,
		W.TFMC_address,
		W.TFMC_city,
		W.TFMC_country_code,
		W.TFMC_state,
		W.TFMC_occupation,
		W.TFMC_from_country,
		CASE 
		WHEN CR_DR_IND = 'D' THEN 'FTCAS'
		WHEN CR_DR_IND = 'C' THEN 'FTDEP' 
		END AS TTMC_to_funds_code,
		'UBL Bank Limited' AS TTMC_institution_name,
		'43' AS TTMC_institution_code,
		'FALSE' AS TTMC_non_bank_institution,
		BB.BRNCH_DESC || ' (' || T.ACCT_BRNCH_SROGT_ID || ')'  AS TTMC_branch,
		T.ACCT_SROGT_ID AS TTMC_account,
		T.ACCT_CURY_EDW_ID AS TTMC_currency_code,
		T.FRGN_CCY AS TTMC_Foreign_Currency_Code,
		T.FRGN_TSACTN_AMT AS TTMC_Foreign_Amount,
		T.EXCHANGE_RATE AS TTMC_Foreign_Exchange_Rate,
		T.ACCT_DESC AS TTMC_account_name,
		T.ACCT_TYPE_DESC AS TTMC_Acct_Type_Desc,
		T.ACCT_TYPE_CODE AS TTMC_personal_account_type,
		T.ACCT_DESC AS TTMC_name,
		T.CATEGORY_TYPE_CODE AS TTMC_incorporation_legal_form,
		T.CATEGORY_TYPE_DESC AS TTMC_Category_Type_Desc,
		OREPLACE(BUS.BUSINESS_DESC, '"', '') AS TTMC_business,

		case when d.MBL_NUM is not null and d.MBL_NUM <> '' then 'PAPVT' 
				  when d.MBL_NUM is null OR d.MBL_NUM = '' then 'PAOFF' end as TTMC_tph_contact_type,
		case when d.MBL_NUM is not null and d.MBL_NUM <> '' then 'COMOB' else 'COLAN' end as TTMC_tph_communication_type,
		'92' as TTMC_tph_country_prefix,			  
        CASE
			when D.MBL_NUM is not null AND D.MBL_NUM <> ''  
			THEN CASE WHEN REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' ) IS NULL OR REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' ) = ''
						THEN TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') ) ELSE REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' )  END
	        when D.PHN_RSDNC is not null AND D.PHN_RSDNC <> '' then TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.PHN_RSDNC), '[^ ]+', 1, 1), '[^0-9]', '') )
	        else 
			case 
				WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' AND REGEXP_SIMILAR(D.PHN_BUSN, '.*[0-9].*') = '1' THEN CAST(NULL AS VARCHAR(11))
				WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' THEN CAST(NULL AS VARCHAR(11))
				ELSE 
					case
						when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,3) = '092' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3) 
						when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,2) = '92' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3)  
						ELSE trim(LEADING '0' FROM regexp_replace(D.PHN_BUSN, '[^0-9]', ''))
					end
			end 
		END as TTMC_tph_number, 				  

		case when d.PERM_ADDR is not null and d.PERM_ADDR <> '' then 'PAPVT' 
					when d.PERM_ADDR is null OR d.PERM_ADDR = '' then 'PAOFF' end as TTMC_address_type,

	   TRIM(OREPLACE(OREPLACE( 
		CASE 
		WHEN TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is not null AND TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3
		              THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' ')  , '[[:space:]]+', ' '))  
		WHEN (TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
				       AND (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
				      THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' ')) 
		WHEN (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
				       AND ( TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
					   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))
		WHEN (TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3 ) 
				       AND (TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
					   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))		   
		ELSE CAST(NULL AS VARCHAR(10)) 
		END
		,CHR(13),' '),CHR(10), ' ')) as TTMC_address,
		BB.CITY_NAME AS TTMC_city,
		'PK' as TTMC_country_code,
		CASE WHEN BB.PROV_NAME = 'FATA' THEN 'KHYBER-PAKHTUNKHWA'
					WHEN BB.PROV_NAME = 'ISLAMABAD' THEN 'PUNJAB'
					ELSE BB.PROV_NAME 
		END AS TTMC_State,
		'PK' AS TTMC_incorporation_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN 
					CASE 
					 WHEN d.GNDR IS NOT NULL THEN d.GNDR
					 WHEN d.GNDR IS NULL THEN 
								CASE WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'M' 
								WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'F' 
								ELSE CAST(NULL AS VARCHAR(10)) END END
			END
		) AS DIR1_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN 
					CASE 
					 WHEN d.TITL IS NOT NULL THEN d.TITL
					 WHEN d.TITL IS NULL THEN 
								CASE WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'MR' 
								WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'MS'
								ELSE CAST(NULL AS VARCHAR(10)) END END
			END
		) AS DIR1_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z0-9 ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
						FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
			END
		) AS DIR1_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN 
				CASE WHEN  REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0 
							THEN  TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
				              			  POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) )
							ELSE 
									CASE WHEN (D.FRST_NAME IS NULL AND D.MDL_NAME IS NULL AND D.LAST_NAME IS NULL) OR (D.FRST_NAME = '' AND D.MDL_NAME = '' AND D.LAST_NAME = '')
												THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
												 			FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
												ELSE 
														CASE WHEN REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0
																	THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
													            				POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) 
														ELSE TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
																 	FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
														END
									END
				END
			END
		) AS DIR1_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN TO_CHAR(D.DT_OF_BIRTH , 'YYYY-MM-DD') ||  'T00:00:00' 
			END
		) AS DIR1_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.FTHR_NAME, '[^A-Za-z ]', ' '), ' +', ' '))
			END
		) AS DIR1_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN D.IDNTFTN_TYPE_EDW_ID 
			END
		) AS DIR1_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN
							CASE WHEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) = '' THEN CAST(NULL AS VARCHAR(10)) 
											   ELSE TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) END
			END
		) AS DIR1_SSN

		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN D.CTRY_OF_NTLTY
			END
		) AS DIR1_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN 'PK'
			END
		) AS DIR1_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN
						  CASE WHEN D.MBL_NUM is not null AND D.MBL_NUM <> '' then 'PAPVT' when D.MBL_NUM is null OR D.MBL_NUM = '' then 'PAOFF' END
			END
		) AS DIR1_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN
						  CASE WHEN D.MBL_NUM is not null AND D.MBL_NUM <> '' then 'COMOB' else 'COLAN' END
			END
		) AS DIR1_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN '92'
			END
		) AS DIR1_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN 		
			
			CASE when D.MBL_NUM is not null AND D.MBL_NUM <> ''  
			THEN CASE WHEN REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' ) IS NULL OR REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' ) = ''
						THEN TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') ) ELSE REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' )  END
	        when D.PHN_RSDNC is not null AND D.PHN_RSDNC <> '' then TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.PHN_RSDNC), '[^ ]+', 1, 1), '[^0-9]', '') )
	        else case WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' AND REGEXP_SIMILAR(D.PHN_BUSN, '.*[0-9].*') = '1' THEN CAST(NULL AS VARCHAR(11)) WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' THEN CAST(NULL AS VARCHAR(11))
			ELSE case when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,3) = '092' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3) when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,2) = '92' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3)  
			ELSE trim(LEADING '0' FROM regexp_replace(D.PHN_BUSN, '[^0-9]', '')) end end END	
			END
		) AS DIR1_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN
						 CASE WHEN D.PERM_ADDR is not null and D.PERM_ADDR <> '' then 'PAPVT' 
									 WHEN D.PERM_ADDR is null OR D.PERM_ADDR = '' then 'PAOFF' END
			END
		) AS DIR1_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN 
				CASE 
				WHEN TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is not null AND TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3
				              THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' ')  , '[[:space:]]+', ' '))  
				WHEN (TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
						       AND (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
						      THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' ')) 
				WHEN (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
						       AND ( TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))
				WHEN (TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3 ) 
						       AND (TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))		   
				ELSE CAST(NULL AS VARCHAR(10)) 
				END
			END
		) AS DIR1_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CASE WHEN TRIM(D.RSDNTL_CITY)  = '0' THEN CAST(NULL AS VARCHAR(10)) ELSE D.RSDNTL_CITY END 
			END
		) AS DIR1_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN 'PK'
			END
		) AS DIR1_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN 
						 CASE  
							when substr(D.IDNTFTN_VAL,1,1) IN ('1', '2') then 'KHYBER-PAKHTUNKHWA'
							when substr(D.IDNTFTN_VAL,1,1) IN ('3', '6') then 'PUNJAB'
							when substr(D.IDNTFTN_VAL,1,1) = '4' then 'SINDH'
							when substr(D.IDNTFTN_VAL,1,1) = '5' then 'BALOCHISTAN'
							when substr(D.IDNTFTN_VAL,1,1) = '7' then 'GILGIT-BALISTAN'
							when substr(D.IDNTFTN_VAL,1,1) = '8' then 'AZAD-KASHMIR'
							ELSE cast(null as varchar(10)) 
						END 
			END
		) AS DIR1_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN  CASE WHEN _DO.OCPTN_DESC IS NOT NULL OR _DO.OCPTN_DESC <> '' THEN _DO.OCPTN_DESC ELSE 'Others' END 
			END
		) AS DIR1_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR1_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_FATHER_NAME

        , MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR2_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS DIR3_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR3_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR4_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR5_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_SSN

		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR6_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR7_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR8_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 9  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR9_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS DIR10_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 10  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR10_ROLE
	
		, CASE WHEN TRIM(LEADING '0' FROM REGEXP_REPLACE(D.TAX_NUM, '[^0-9]', '')) = '' THEN NULL 
		ELSE TRIM(LEADING '0' FROM REGEXP_REPLACE(D.TAX_NUM, '[^0-9]', '')) END AS TMC_TAX_NUM
		
		
		, MAX('TRUE') AS SIGNATORY1_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 1  THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 1 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND  DD.D_RN IS NULL THEN 
						CASE 
							 WHEN d.GNDR IS NOT NULL THEN d.GNDR
							 WHEN d.GNDR IS NULL THEN 
										CASE WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'M' 
										WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'F' 
										ELSE CAST(NULL AS VARCHAR(10)) END END
			END
		) AS SIGNATORY1_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN 
					CASE 
					 WHEN d.TITL IS NOT NULL THEN d.TITL
					 WHEN d.TITL IS NULL THEN 
								CASE WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'MR' 
								WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'MS'
								ELSE CAST(NULL AS VARCHAR(10)) END END
			END
		) AS SIGNATORY1_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 1  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN  TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
						FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
			END
		) AS SIGNATORY1_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 1  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN 
					CASE WHEN  REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0 
								THEN  TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
					              			  POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) )
								ELSE 
										CASE WHEN (D.FRST_NAME IS NULL AND D.MDL_NAME IS NULL AND D.LAST_NAME IS NULL) OR (D.FRST_NAME = '' AND D.MDL_NAME = '' AND D.LAST_NAME = '')
													THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
													 			FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
													ELSE 
															CASE WHEN REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0
																		THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
														            				POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) 
															ELSE TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
																	 	FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
															END
										END
					END
			END
		) AS SIGNATORY1_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.FTHR_NAME, '[^A-Za-z ]', ' '), ' +', ' '))
			END
		) AS SIGNATORY1_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN D.IDNTFTN_TYPE_EDW_ID 
			END
		) AS SIGNATORY1_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN 
							CASE WHEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) = '' THEN CAST(NULL AS VARCHAR(10)) 
															   ELSE TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) END
			END
		) AS SIGNATORY1_SSN
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN D.CTRY_OF_NTLTY
			END
		) AS SIGNATORY1_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN 'PK'
			END
		) AS SIGNATORY1_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN 
						  CASE WHEN D.MBL_NUM is not null AND D.MBL_NUM <> '' then 'PAPVT' when D.MBL_NUM is null OR D.MBL_NUM = '' then 'PAOFF' END
			END
		) AS SIGNATORY1_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN 
						  CASE WHEN D.MBL_NUM is not null AND D.MBL_NUM <> '' then 'COMOB' else 'COLAN' END
			END
		) AS SIGNATORY1_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN '92'
			END
		) AS SIGNATORY1_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN 
			CASE when D.MBL_NUM is not null AND D.MBL_NUM <> ''  
			THEN CASE WHEN REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' ) IS NULL OR REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' ) = ''
						THEN TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') ) ELSE REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' )  END
	        when D.PHN_RSDNC is not null AND D.PHN_RSDNC <> '' then TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.PHN_RSDNC), '[^ ]+', 1, 1), '[^0-9]', '') )
	        else case WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' AND REGEXP_SIMILAR(D.PHN_BUSN, '.*[0-9].*') = '1' THEN CAST(NULL AS VARCHAR(11)) WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' THEN CAST(NULL AS VARCHAR(11))
			ELSE case when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,3) = '092' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3) when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,2) = '92' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3)  
			ELSE trim(LEADING '0' FROM regexp_replace(D.PHN_BUSN, '[^0-9]', '')) end end END	
			END
		) AS SIGNATORY1_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN TO_CHAR(D.DT_OF_BIRTH , 'YYYY-MM-DD') ||  'T00:00:00'
			END
		) AS SIGNATORY1_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CASE WHEN D.PERM_ADDR is not null and D.PERM_ADDR <> '' then 'PAPVT'  WHEN D.PERM_ADDR is null OR D.PERM_ADDR = '' then 'PAOFF' END
			END
		) AS SIGNATORY1_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN
			CASE 
				WHEN TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is not null AND TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3
				              THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' ')  , '[[:space:]]+', ' '))  
				WHEN (TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
						       AND (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
						      THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' ')) 
				WHEN (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
						       AND ( TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))
				WHEN (TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3 ) 
						       AND (TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))		   
				ELSE CAST(NULL AS VARCHAR(10)) 
				END
			END
		) AS SIGNATORY1_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CASE WHEN TRIM(D.RSDNTL_CITY)  = '0' THEN CAST(NULL AS VARCHAR(10)) ELSE D.RSDNTL_CITY END
			END
		) AS SIGNATORY1_CITY
	
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN 'PK'
			END
		) AS SIGNATORY1_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN 
						  CASE  
							when substr(D.IDNTFTN_VAL,1,1) IN ('1', '2') then 'KHYBER-PAKHTUNKHWA'
							when substr(D.IDNTFTN_VAL,1,1) IN ('3', '6') then 'PUNJAB'
							when substr(D.IDNTFTN_VAL,1,1) = '4' then 'SINDH'
							when substr(D.IDNTFTN_VAL,1,1) = '5' then 'BALOCHISTAN'
							when substr(D.IDNTFTN_VAL,1,1) = '7' then 'GILGIT-BALISTAN'
							when substr(D.IDNTFTN_VAL,1,1) = '8' then 'AZAD-KASHMIR'
							ELSE cast(null as varchar(10)) 
						END
			END
		) AS SIGNATORY1_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CASE WHEN _DO.OCPTN_DESC IS NOT NULL OR _DO.OCPTN_DESC <> '' THEN _DO.OCPTN_DESC ELSE 'Others' END 
			END
		) AS SIGNATORY1_OCCUPATION
		
		, MAX(
			'ARPYS' 
		) AS SIGNATORY1_ROLE
		
		-----------------------------------------------------------------------------------------------------------------------------------------------------------
		, MAX('TRUE') AS SIGNATORY2_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 2 THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 2 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2 THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 2  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY2_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 2  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY2_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY2_SSN
		
		 , MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_CITY
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 2 THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_OCCUPATION
		
		, MAX(
			'ARPYS'
		) AS SIGNATORY2_ROLE
		 
		, MAX('TRUE') AS SIGNATORY3_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 3 THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 3 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3 THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 3  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY3_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 3  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY3_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY3_SSN
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_CITY
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 3 THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_OCCUPATION
		
		, MAX(
			'ARPYS'
		) AS SIGNATORY3_ROLE
		
		, MAX('TRUE') AS SIGNATORY4_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 4 THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 4 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4 THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 4  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY4_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 4  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY4_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY4_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY4_SSN
		
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_CITY
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 4 THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_OCCUPATION
		
		, MAX(
			'ARPYS'
		) AS SIGNATORY4_ROLE
		
		, MAX('TRUE') AS SIGNATORY5_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 5 THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 5 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5 THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 5  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY5_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 5  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY5_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY5_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY5_SSN
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_CITY
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 5 THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_OCCUPATION
		
		, MAX(
			'ARPYS'
		) AS SIGNATORY5_ROLE
		
		, MAX('TRUE') AS SIGNATORY6_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 6 THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 6 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6 THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 6  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY6_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 6  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY6_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY6_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY6_SSN
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_CITY
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 6 THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_OCCUPATION
		
		, MAX(
			'ARPYS'
		) AS SIGNATORY6_ROLE
		
		, MAX('TRUE') AS SIGNATORY7_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 7 THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 7 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7 THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 7  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY7_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 7  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY7_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY7_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY7_SSN
		
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_CITY
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 7 THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_OCCUPATION
		
		, MAX(
			'ARPYS'
		) AS SIGNATORY7_ROLE
		
		, MAX('TRUE') AS SIGNATORY8_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 8 THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 8 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8 THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 8  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY8_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 8  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY8_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY8_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY8_SSN
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_CITY
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 8 THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_OCCUPATION
		
		, MAX(
			'ARPYS'
		) AS SIGNATORY8_ROLE
		
		, TO_CHAR(T.ACCT_ORIGNL_OPN_DT , 'YYYY-MM-DD') ||  'T00:00:00' AS TTMC_open,
		'ASACT' as TTMC_status_code,
		'PK' AS TTMC_to_country

		FROM TRXNS T
		LEFT JOIN DP_SDMVW_DFDN.DIM_CUST_VW d ON d.CUST_SROGT_ID = T.CUST_SROGT_ID and d.system_code = 'CBS'
		LEFT JOIN DP_SDMT_DFDN.DIM_OCPTN_SS _DO ON D.OCPTN_EDW_ID = _DO.OCPTN_EDW_ID
		LEFT JOIN DP_WRK_CBS.FM_CLIENT_DAILY fmd ON fmd.client_no = T.CUST_SROGT_ID
		LEFT JOIN DP_SDMVW_DFDN.DIM_BUSINESS_VW BUS ON fmd.business = bus.BUSINESS
		LEFT JOIN DP_SDMVW_DFDN.DIM_CUST_TYPE_VW CTY ON D.CUST_TYPE_EDW_ID = CTY.CUST_TYPE_EDW_ID
		LEFT JOIN DP_SDMVW_DFDN.DIM_BRNCH_HIERARCHY_VW B ON T.BRNCH_SROGT_ID = B.BRNCH_SROGT_ID
		LEFT JOIN DP_SDMVW_DFDN.DIM_BRNCH_HIERARCHY_VW BB ON T.ACCT_BRNCH_SROGT_ID = BB.BRNCH_SROGT_ID 
		LEFT JOIN MANDATE M ON M.ACCT_SROGT_ID = T.ACCT_SROGT_ID
		LEFT JOIN DIRECTORS DD ON DD.CUST_SROGT_ID = T.CUST_SROGT_ID 
		LEFT JOIN WALKIN_DETAILS W ON W.Transaction_ID = T.TSACTN_ID
		WHERE 1=1 
		GROUP BY 
		CATEGORY, CATEGORY_TYPE_DESC,transactionnumber,transaction_location,transaction_description,date_transaction,teller,authorized,transmode_code,amount_local,TFMC_from_funds_code,TFMC_Gender,
		TFMC_Title,TFMC_First_Name,TFMC_Last_Name,TFMC_Birth_Date,TFMC_Mother_Name,TFMC_ssn_type,TFMC_ssn,TFMC_nationality1,TFMC_Residence,TFMC_tph_contact_type,
		TFMC_tph_communication_type,TFMC_tph_country_prefix,TFMC_tph_number,TFMC_address_type,TFMC_address,TFMC_city,TFMC_country_code,TFMC_state,TFMC_occupation,
		TFMC_from_country,TTMC_to_funds_code,TTMC_institution_name,TTMC_institution_code,TTMC_non_bank_institution,TTMC_branch,TTMC_account,TTMC_currency_code,
		TTMC_Foreign_Currency_Code, TTMC_Foreign_Amount, TTMC_Foreign_Exchange_Rate, TTMC_account_name,TTMC_Acct_Type_Desc,TTMC_personal_account_type,TTMC_name,TTMC_incorporation_legal_form, TTMC_Category_Type_Desc,
		TTMC_business,TTMC_tph_contact_type,TTMC_tph_communication_type, TTMC_tph_country_prefix,TTMC_tph_number,TTMC_address_type,TTMC_address,TTMC_city,TTMC_country_code,
		TTMC_state,TTMC_incorporation_country_code,TMC_TAX_NUM, TTMC_open,TTMC_status_code,TTMC_to_country 
		)

		, DATA_V1 AS ( 
		
		SELECT 
		CAST(CATEGORY AS VARCHAR(10)) AS CATEGORY, 
	    CAST(CATEGORY_TYPE_DESC AS VARCHAR(99)) AS SYS_CATEGORY,
		CAST(transactionnumber AS BIGINT) AS transactionnumber,
		CAST(transaction_location AS VARCHAR(99)) AS transaction_location,
		CAST(transaction_description AS VARCHAR(99)) AS transaction_description,
		CAST(date_transaction AS VARCHAR(20)) AS date_transaction,
		CAST(teller AS VARCHAR(99)) AS teller ,
		CAST(authorized AS VARCHAR(99)) AS authorized,
		CAST(transmode_code AS VARCHAR(10)) AS transmode_code,
		CAST(amount_local AS INT) AS amount_local,
	    CAST(TFMC_from_funds_code AS VARCHAR(10)) AS TFMC_from_funds_code,
		CAST(TFMC_Gender AS VARCHAR(10)) AS TFMC_Gender,
		CAST(TFMC_Title AS VARCHAR(99)) AS TFMC_Title,
		CAST(TFMC_First_Name AS VARCHAR(99)) AS TFMC_First_Name,
		CAST(TFMC_Last_Name AS VARCHAR(99)) AS TFMC_Last_Name,
		CASE WHEN TFMC_Birth_Date LIKE '00%'  THEN '19' || SUBSTR(TFMC_Birth_Date, 3) ELSE TFMC_Birth_Date END AS TFMC_Birth_Date,
		--CAST(TFMC_Birth_Date AS VARCHAR(20)) AS TFMC_Birth_Date,
		CAST(TFMC_Mother_Name AS VARCHAR(99)) AS TFMC_Mother_Name,
		CAST(TFMC_ssn_type AS VARCHAR(10)) AS TFMC_ssn_type,
		CAST(CASE WHEN TFMC_ssn_type IN ('NIC', 'PPT','POC') THEN TFMC_ssn ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS TFMC_ssn,
		CAST(CASE WHEN TFMC_ssn_type= 'NIC' THEN 'PK' ELSE TFMC_nationality1 END  AS VARCHAR(20)) AS TFMC_nationality1, 
		CAST(TFMC_Residence AS VARCHAR(20)) AS TFMC_Residence,
		CAST(TFMC_tph_contact_type AS VARCHAR(20)) AS TFMC_tph_contact_type,
		CAST(TFMC_tph_communication_type AS VARCHAR(20)) AS TFMC_tph_communication_type,
		CAST(TFMC_tph_country_prefix AS VARCHAR(10)) AS TFMC_tph_country_prefix,
		CAST(TFMC_tph_number AS VARCHAR(20)) AS TFMC_tph_number,
		CAST(TFMC_address_type AS VARCHAR(10)) AS TFMC_address_type,
		CAST(TFMC_address AS VARCHAR(99)) AS TFMC_address,
		CAST(TFMC_city AS VARCHAR(50)) AS TFMC_city,
		CAST(TFMC_country_code AS VARCHAR(10)) AS TFMC_country_code,
		CAST(TFMC_state AS VARCHAR(50)) AS TFMC_state,
		CAST(TFMC_occupation AS VARCHAR(99)) AS TFMC_occupation,
		CAST(TFMC_from_country AS VARCHAR(20)) AS TFMC_from_country,
		CAST(TTMC_to_funds_code AS VARCHAR(20)) AS TTMC_to_funds_code,
		CAST(TTMC_institution_name AS VARCHAR(99)) AS TTMC_institution_name,
		CAST(TTMC_institution_code AS VARCHAR(99)) AS TTMC_institution_code,
		CAST(TTMC_non_bank_institution AS VARCHAR(99)) AS TTMC_non_bank_institution,
		CAST(TTMC_branch AS VARCHAR(99)) AS TTMC_branch,
		CAST(TTMC_account AS VARCHAR(20)) AS TTMC_account,
		CAST(TTMC_currency_code AS VARCHAR(10)) AS TTMC_currency_code,
		CAST(TTMC_Foreign_Currency_Code AS VARCHAR(10)) AS TTMC_Foreign_Currency_Code,
		CAST(TTMC_Foreign_Amount AS INT) AS TTMC_Foreign_Amount  ,
		CAST(TTMC_Foreign_Exchange_Rate AS DECIMAL(38,4)) AS TTMC_Foreign_Exchange_Rate,
		CAST(TTMC_account_name AS VARCHAR(99)) AS TTMC_account_name, 
		CAST(TTMC_personal_account_type AS VARCHAR(20)) AS TTMC_personal_account_type, 
		CAST(TTMC_name AS VARCHAR(99)) AS TTMC_name, 
		CAST(TTMC_incorporation_legal_form AS VARCHAR(20)) AS TTMC_incorporation_legal_form, 
		CAST(TTMC_business AS VARCHAR(99)) AS TTMC_business, 
		CAST(TTMC_tph_contact_type AS VARCHAR(20)) AS TTMC_tph_contact_type, 
		CAST(TTMC_tph_communication_type AS VARCHAR(20)) AS TTMC_tph_communication_type, 
		CAST(TTMC_tph_country_prefix AS VARCHAR(10)) AS TTMC_tph_country_prefix ,
		CAST(CASE WHEN TTMC_tph_number IS NULL OR TTMC_tph_number = '' THEN COALESCE(SIGNATORY1_TPH_NUMBER, DIR1_TPH_NUMBER) ELSE TTMC_tph_number END AS VARCHAR(20)) AS TTMC_tph_number,
		CAST(TTMC_address_type AS VARCHAR(10)) AS TTMC_address_type,
		CAST(CASE WHEN TTMC_address IS NULL OR TTMC_address = '' THEN COALESCE(SIGNATORY1_ADDRESS, DIR1_ADDRESS) ELSE TTMC_address END AS VARCHAR(99)) AS TTMC_address,
		CAST(TTMC_city AS VARCHAR(50)) AS TTMC_city,
		CAST(TTMC_country_code AS VARCHAR(10)) AS TTMC_country_code,
		CAST(TTMC_state AS VARCHAR(50)) AS TTMC_state,
		CAST(TTMC_incorporation_country_code AS VARCHAR(20)) AS TTMC_incorporation_country_code,
		------------------------------------- DIRECTOR 1 -----------------------------------------
		CAST(DIR1_GNDR AS VARCHAR(10)) AS DIR1_GNDR,
		CAST(DIR1_TITL AS VARCHAR(10)) AS DIR1_TITL,
		CAST(DIR1_FIRSTNAME AS VARCHAR(99)) AS DIR1_FIRSTNAME,
		CAST(DIR1_LASTNAME AS VARCHAR(99)) AS DIR1_LASTNAME,
		CAST(DIR1_FATHER_NAME AS VARCHAR(99)) AS DIR1_FATHER_NAME,
		CAST(DIR1_SSN_TYPE AS VARCHAR(10)) AS DIR1_SSN_TYPE,
		CAST(CASE WHEN DIR1_SSN_TYPE IN ('NIC', 'PPT','POC') THEN DIR1_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR1_SSN,
	    CAST(DIR1_nationality1 AS VARCHAR(10)) AS DIR1_nationality1,
	    CAST(DIR1_Residence AS VARCHAR(10)) AS DIR1_Residence,
	    CAST(DIR1_tph_contact_type AS VARCHAR(10)) AS DIR1_tph_contact_type,
	    CAST(DIR1_tph_communication_type AS VARCHAR(10)) AS DIR1_tph_communication_type,
	    CAST(DIR1_tph_country_prefix AS VARCHAR(10)) AS DIR1_tph_country_prefix,
		CAST(CASE WHEN DIR1_TPH_NUMBER IS NULL OR DIR1_TPH_NUMBER = '' THEN 
					COALESCE(CASE WHEN SIGNATORY1_TPH_NUMBER IS NULL OR SIGNATORY1_TPH_NUMBER = '' THEN TTMC_tph_number END, SIGNATORY1_TPH_NUMBER ) ELSE DIR1_TPH_NUMBER END AS VARCHAR(50)) AS DIR1_TPH_NUMBER,
		CAST(CASE WHEN DIR1_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR1_DATE_OF_BIRTH, 3) ELSE DIR1_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR1_DATE_OF_BIRTH,
	    CAST(DIR1_address_type AS VARCHAR(10)) AS DIR1_address_type,
		CAST(DIR1_ADDRESS AS VARCHAR(99)) AS DIR1_ADDRESS,
	    CAST(DIR1_CITY AS VARCHAR(20)) AS DIR1_CITY,
	    CAST(DIR1_country_code AS VARCHAR(10)) AS DIR1_country_code,
	    CAST(DIR1_STATE AS VARCHAR(20)) AS DIR1_STATE,
		CAST(DIR1_OCCUPATION AS VARCHAR(99)) AS DIR1_OCCUPATION,
	    CAST(DIR1_ROLE AS VARCHAR(10)) AS DIR1_ROLE,
		------------------------------------- DIRECTOR 2 -----------------------------------------
		CAST(DIR2_GNDR AS VARCHAR(10)) AS DIR2_GNDR,
		CAST(DIR2_TITL AS VARCHAR(10)) AS DIR2_TITL,
		CAST(DIR2_FIRSTNAME AS VARCHAR(99)) AS DIR2_FIRSTNAME,
		CAST(DIR2_LASTNAME AS VARCHAR(99)) AS DIR2_LASTNAME,
		CAST(DIR2_FATHER_NAME AS VARCHAR(99)) AS DIR2_FATHER_NAME,
		CAST(DIR2_SSN_TYPE AS VARCHAR(10)) AS DIR2_SSN_TYPE,
		CAST(CASE WHEN DIR2_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR2_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR2_SSN,
	    CAST(DIR2_nationality1 AS VARCHAR(10)) AS DIR2_nationality1,
	    CAST(DIR2_Residence AS VARCHAR(10)) AS DIR2_Residence,
	    CAST(DIR2_tph_contact_type AS VARCHAR(10)) AS DIR2_tph_contact_type,
	    CAST(DIR2_tph_communication_type AS VARCHAR(10)) AS DIR2_tph_communication_type,
	    CAST(DIR2_tph_country_prefix AS VARCHAR(10)) AS DIR2_tph_country_prefix,
		CAST(DIR2_TPH_NUMBER AS VARCHAR(20)) AS DIR2_TPH_NUMBER,
		CAST(CASE WHEN DIR2_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR2_DATE_OF_BIRTH, 3) ELSE DIR2_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR2_DATE_OF_BIRTH,
	    CAST(DIR2_address_type AS VARCHAR(10)) AS DIR2_address_type,
		CAST(DIR2_ADDRESS AS VARCHAR(99)) AS DIR2_ADDRESS,
	    CAST(DIR2_CITY AS VARCHAR(20)) AS DIR2_CITY,
	    CAST(DIR2_country_code AS VARCHAR(10)) AS DIR2_country_code,
	    CAST(DIR2_STATE AS VARCHAR(20)) AS DIR2_STATE,
		CAST(DIR2_OCCUPATION AS VARCHAR(99)) AS DIR2_OCCUPATION,
	    CAST(CASE WHEN DIR2_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR2_ROLE END AS VARCHAR(10)) AS DIR2_ROLE,
		------------------------------------- DIRECTOR 3 -----------------------------------------
		CAST(DIR3_GNDR AS VARCHAR(10)) AS DIR3_GNDR,
		CAST(DIR3_TITL AS VARCHAR(10)) AS DIR3_TITL,
		CAST(DIR3_FIRSTNAME AS VARCHAR(99)) AS DIR3_FIRSTNAME,
		CAST(DIR3_LASTNAME AS VARCHAR(99)) AS DIR3_LASTNAME,
		CAST(DIR3_FATHER_NAME AS VARCHAR(99)) AS DIR3_FATHER_NAME,
		CAST(DIR3_SSN_TYPE AS VARCHAR(10)) AS DIR3_SSN_TYPE,
		CAST(CASE WHEN DIR3_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR3_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR3_SSN,
	    CAST(DIR3_nationality1 AS VARCHAR(10)) AS DIR3_nationality1,
	    CAST(DIR3_Residence AS VARCHAR(10)) AS DIR3_Residence,
	    CAST(DIR3_tph_contact_type AS VARCHAR(10)) AS DIR3_tph_contact_type,
	    CAST(DIR3_tph_communication_type AS VARCHAR(10)) AS DIR3_tph_communication_type,
	    CAST(DIR3_tph_country_prefix AS VARCHAR(10)) AS DIR3_tph_country_prefix,
		CAST(DIR3_TPH_NUMBER AS VARCHAR(20)) AS DIR3_TPH_NUMBER,
		CAST(CASE WHEN DIR3_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR3_DATE_OF_BIRTH, 3) ELSE DIR3_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR3_DATE_OF_BIRTH,
	    CAST(DIR3_address_type AS VARCHAR(10)) AS DIR3_address_type,
		CAST(DIR3_ADDRESS AS VARCHAR(99)) AS DIR3_ADDRESS,
	    CAST(DIR3_CITY AS VARCHAR(20)) AS DIR3_CITY,
	    CAST(DIR3_country_code AS VARCHAR(10)) AS DIR3_country_code,
	    CAST(DIR3_STATE AS VARCHAR(20)) AS DIR3_STATE,
		CAST(DIR3_OCCUPATION AS VARCHAR(99)) AS DIR3_OCCUPATION,
	    CAST(CASE WHEN DIR3_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR3_ROLE END AS VARCHAR(10)) AS DIR3_ROLE,
		------------------------------------- DIRECTOR 4 -----------------------------------------
		CAST(DIR4_GNDR AS VARCHAR(10)) AS DIR4_GNDR,
		CAST(DIR4_TITL AS VARCHAR(10)) AS DIR4_TITL,
		CAST(DIR4_FIRSTNAME AS VARCHAR(99)) AS DIR4_FIRSTNAME,
		CAST(DIR4_LASTNAME AS VARCHAR(99)) AS DIR4_LASTNAME,
		CAST(DIR4_FATHER_NAME AS VARCHAR(99)) AS DIR4_FATHER_NAME,
		CAST(DIR4_SSN_TYPE AS VARCHAR(10)) AS DIR4_SSN_TYPE,
		CAST(CASE WHEN DIR4_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR4_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR4_SSN,
	    CAST(DIR4_nationality1 AS VARCHAR(10)) AS DIR4_nationality1,
	    CAST(DIR4_Residence AS VARCHAR(10)) AS DIR4_Residence,
	    CAST(DIR4_tph_contact_type AS VARCHAR(10)) AS DIR4_tph_contact_type,
	    CAST(DIR4_tph_communication_type AS VARCHAR(10)) AS DIR4_tph_communication_type,
	    CAST(DIR4_tph_country_prefix AS VARCHAR(10)) AS DIR4_tph_country_prefix,
		CAST(DIR4_TPH_NUMBER AS VARCHAR(20)) AS DIR4_TPH_NUMBER,
		CAST(CASE WHEN DIR4_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR4_DATE_OF_BIRTH, 3) ELSE DIR4_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR4_DATE_OF_BIRTH,
	    CAST(DIR4_address_type AS VARCHAR(10)) AS DIR4_address_type,
		CAST(DIR4_ADDRESS AS VARCHAR(99)) AS DIR4_ADDRESS,
	    CAST(DIR4_CITY AS VARCHAR(20)) AS DIR4_CITY,
	    CAST(DIR4_country_code AS VARCHAR(10)) AS DIR4_country_code,
	    CAST(DIR4_STATE AS VARCHAR(20)) AS DIR4_STATE,
		CAST(DIR4_OCCUPATION AS VARCHAR(99)) AS DIR4_OCCUPATION,
	    CAST(CASE WHEN DIR4_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR4_ROLE END AS VARCHAR(10)) AS DIR4_ROLE,
		------------------------------------- DIRECTOR 5 -----------------------------------------
		CAST(DIR5_GNDR AS VARCHAR(10)) AS DIR5_GNDR,
		CAST(DIR5_TITL AS VARCHAR(10)) AS DIR5_TITL,
		CAST(DIR5_FIRSTNAME AS VARCHAR(99)) AS DIR5_FIRSTNAME,
		CAST(DIR5_LASTNAME AS VARCHAR(99)) AS DIR5_LASTNAME,
		CAST(DIR5_FATHER_NAME AS VARCHAR(99)) AS DIR5_FATHER_NAME,
		CAST(DIR5_SSN_TYPE AS VARCHAR(10)) AS DIR5_SSN_TYPE,
		CAST(CASE WHEN DIR5_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR5_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR5_SSN,
	    CAST(DIR5_nationality1 AS VARCHAR(10)) AS DIR5_nationality1,
	    CAST(DIR5_Residence AS VARCHAR(10)) AS DIR5_Residence,
	    CAST(DIR5_tph_contact_type AS VARCHAR(10)) AS DIR5_tph_contact_type,
	    CAST(DIR5_tph_communication_type AS VARCHAR(10)) AS DIR5_tph_communication_type,
	    CAST(DIR5_tph_country_prefix AS VARCHAR(10)) AS DIR5_tph_country_prefix,
		CAST(DIR5_TPH_NUMBER AS VARCHAR(20)) AS DIR5_TPH_NUMBER,
		CAST(CASE WHEN DIR5_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR5_DATE_OF_BIRTH, 3) ELSE DIR5_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR5_DATE_OF_BIRTH,
	    CAST(DIR5_address_type AS VARCHAR(10)) AS DIR5_address_type,
		CAST(DIR5_ADDRESS AS VARCHAR(99)) AS DIR5_ADDRESS,
	    CAST(DIR5_CITY AS VARCHAR(20)) AS DIR5_CITY,
	    CAST(DIR5_country_code AS VARCHAR(10)) AS DIR5_country_code,
	    CAST(DIR5_STATE AS VARCHAR(20)) AS DIR5_STATE,
		CAST(DIR5_OCCUPATION AS VARCHAR(99)) AS DIR5_OCCUPATION,
	    CAST(CASE WHEN DIR5_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR5_ROLE END AS VARCHAR(10)) AS DIR5_ROLE,
		------------------------------------- DIRECTOR 6 -----------------------------------------
		CAST(DIR6_GNDR AS VARCHAR(10)) AS DIR6_GNDR,
		CAST(DIR6_TITL AS VARCHAR(10)) AS DIR6_TITL,
		CAST(DIR6_FIRSTNAME AS VARCHAR(99)) AS DIR6_FIRSTNAME,
		CAST(DIR6_LASTNAME AS VARCHAR(99)) AS DIR6_LASTNAME,
		CAST(DIR6_FATHER_NAME AS VARCHAR(99)) AS DIR6_FATHER_NAME,
		CAST(DIR6_SSN_TYPE AS VARCHAR(10)) AS DIR6_SSN_TYPE,
		CAST(CASE WHEN DIR6_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR6_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR6_SSN,
	    CAST(DIR6_nationality1 AS VARCHAR(10)) AS DIR6_nationality1,
	    CAST(DIR6_Residence AS VARCHAR(10)) AS DIR6_Residence,
	    CAST(DIR6_tph_contact_type AS VARCHAR(10)) AS DIR6_tph_contact_type,
	    CAST(DIR6_tph_communication_type AS VARCHAR(10)) AS DIR6_tph_communication_type,
	    CAST(DIR6_tph_country_prefix AS VARCHAR(10)) AS DIR6_tph_country_prefix,
		CAST(DIR6_TPH_NUMBER AS VARCHAR(20)) AS DIR6_TPH_NUMBER,
		CAST(CASE WHEN DIR6_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR6_DATE_OF_BIRTH, 3) ELSE DIR6_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR6_DATE_OF_BIRTH,
	    CAST(DIR6_address_type AS VARCHAR(10)) AS DIR6_address_type,
		CAST(DIR6_ADDRESS AS VARCHAR(99)) AS DIR6_ADDRESS,
	    CAST(DIR6_CITY AS VARCHAR(20)) AS DIR6_CITY,
	    CAST(DIR6_country_code AS VARCHAR(10)) AS DIR6_country_code,
	    CAST(DIR6_STATE AS VARCHAR(20)) AS DIR6_STATE,
		CAST(DIR6_OCCUPATION AS VARCHAR(99)) AS DIR6_OCCUPATION,
	    CAST(CASE WHEN DIR6_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR6_ROLE END AS VARCHAR(10)) AS DIR6_ROLE,
		------------------------------------- DIRECTOR 7 -----------------------------------------
		CAST(DIR7_GNDR AS VARCHAR(10)) AS DIR7_GNDR,
		CAST(DIR7_TITL AS VARCHAR(10)) AS DIR7_TITL,
		CAST(DIR7_FIRSTNAME AS VARCHAR(99)) AS DIR7_FIRSTNAME,
		CAST(DIR7_LASTNAME AS VARCHAR(99)) AS DIR7_LASTNAME,
		CAST(DIR7_FATHER_NAME AS VARCHAR(99)) AS DIR7_FATHER_NAME,
		CAST(DIR7_SSN_TYPE AS VARCHAR(10)) AS DIR7_SSN_TYPE,
		CAST(CASE WHEN DIR7_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR7_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR7_SSN,
	    CAST(DIR7_nationality1 AS VARCHAR(10)) AS DIR7_nationality1,
	    CAST(DIR7_Residence AS VARCHAR(10)) AS DIR7_Residence,
	    CAST(DIR7_tph_contact_type AS VARCHAR(10)) AS DIR7_tph_contact_type,
	    CAST(DIR7_tph_communication_type AS VARCHAR(10)) AS DIR7_tph_communication_type,
	    CAST(DIR7_tph_country_prefix AS VARCHAR(10)) AS DIR7_tph_country_prefix,
		CAST(DIR7_TPH_NUMBER AS VARCHAR(20)) AS DIR7_TPH_NUMBER,
		CAST(CASE WHEN DIR7_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR7_DATE_OF_BIRTH, 3) ELSE DIR7_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR7_DATE_OF_BIRTH,
	    CAST(DIR7_address_type AS VARCHAR(10)) AS DIR7_address_type,
		CAST(DIR7_ADDRESS AS VARCHAR(99)) AS DIR7_ADDRESS,
	    CAST(DIR7_CITY AS VARCHAR(20)) AS DIR7_CITY,
	    CAST(DIR7_country_code AS VARCHAR(10)) AS DIR7_country_code,
	    CAST(DIR7_STATE AS VARCHAR(20)) AS DIR7_STATE,
		CAST(DIR7_OCCUPATION AS VARCHAR(99)) AS DIR7_OCCUPATION,
	    CAST(CASE WHEN DIR7_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR7_ROLE END AS VARCHAR(10)) AS DIR7_ROLE,
		------------------------------------- DIRECTOR 8 -----------------------------------------
		CAST(DIR8_GNDR AS VARCHAR(10)) AS DIR8_GNDR,
		CAST(DIR8_TITL AS VARCHAR(10)) AS DIR8_TITL,
		CAST(DIR8_FIRSTNAME AS VARCHAR(99)) AS DIR8_FIRSTNAME,
		CAST(DIR8_LASTNAME AS VARCHAR(99)) AS DIR8_LASTNAME,
		CAST(DIR8_FATHER_NAME AS VARCHAR(99)) AS DIR8_FATHER_NAME,
		CAST(DIR8_SSN_TYPE AS VARCHAR(10)) AS DIR8_SSN_TYPE,
		CAST(CASE WHEN DIR8_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR8_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR8_SSN,
	    CAST(DIR8_nationality1 AS VARCHAR(10)) AS DIR8_nationality1,
	    CAST(DIR8_Residence AS VARCHAR(10)) AS DIR8_Residence,
	    CAST(DIR8_tph_contact_type AS VARCHAR(10)) AS DIR8_tph_contact_type,
	    CAST(DIR8_tph_communication_type AS VARCHAR(10)) AS DIR8_tph_communication_type,
	    CAST(DIR8_tph_country_prefix AS VARCHAR(10)) AS DIR8_tph_country_prefix,
		CAST(DIR8_TPH_NUMBER AS VARCHAR(20)) AS DIR8_TPH_NUMBER,
		CAST(CASE WHEN DIR8_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR8_DATE_OF_BIRTH, 3) ELSE DIR8_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR8_DATE_OF_BIRTH,
	    CAST(DIR8_address_type AS VARCHAR(10)) AS DIR8_address_type,
		CAST(DIR8_ADDRESS AS VARCHAR(99)) AS DIR8_ADDRESS,
	    CAST(DIR8_CITY AS VARCHAR(20)) AS DIR8_CITY,
	    CAST(DIR8_country_code AS VARCHAR(10)) AS DIR8_country_code,
	    CAST(DIR8_STATE AS VARCHAR(20)) AS DIR8_STATE,
		CAST(DIR8_OCCUPATION AS VARCHAR(99)) AS DIR8_OCCUPATION,
	    CAST(CASE WHEN DIR8_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR8_ROLE END AS VARCHAR(10)) AS DIR8_ROLE,
		------------------------------------- DIRECTOR 9 -----------------------------------------
		CAST(DIR9_GNDR AS VARCHAR(10)) AS DIR9_GNDR,
		CAST(DIR9_TITL AS VARCHAR(10)) AS DIR9_TITL,
		CAST(DIR9_FIRSTNAME AS VARCHAR(99)) AS DIR9_FIRSTNAME,
		CAST(DIR9_LASTNAME AS VARCHAR(99)) AS DIR9_LASTNAME,
		CAST(DIR9_FATHER_NAME AS VARCHAR(99)) AS DIR9_FATHER_NAME,
		CAST(DIR9_SSN_TYPE AS VARCHAR(10)) AS DIR9_SSN_TYPE,
		CAST(CASE WHEN DIR9_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR9_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR9_SSN,
	    CAST(DIR9_nationality1 AS VARCHAR(10)) AS DIR9_nationality1,
	    CAST(DIR9_Residence AS VARCHAR(10)) AS DIR9_Residence,
	    CAST(DIR9_tph_contact_type AS VARCHAR(10)) AS DIR9_tph_contact_type,
	    CAST(DIR9_tph_communication_type AS VARCHAR(10)) AS DIR9_tph_communication_type,
	    CAST(DIR9_tph_country_prefix AS VARCHAR(10)) AS DIR9_tph_country_prefix,
		CAST(DIR9_TPH_NUMBER AS VARCHAR(20)) AS DIR9_TPH_NUMBER,
		CAST(CASE WHEN DIR9_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR9_DATE_OF_BIRTH, 3) ELSE DIR9_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR9_DATE_OF_BIRTH,
	    CAST(DIR9_address_type AS VARCHAR(10)) AS DIR9_address_type,
		CAST(DIR9_ADDRESS AS VARCHAR(99)) AS DIR9_ADDRESS,
	    CAST(DIR9_CITY AS VARCHAR(20)) AS DIR9_CITY,
	    CAST(DIR9_country_code AS VARCHAR(10)) AS DIR9_country_code,
	    CAST(DIR9_STATE AS VARCHAR(20)) AS DIR9_STATE,
		CAST(DIR9_OCCUPATION AS VARCHAR(99)) AS DIR9_OCCUPATION,
	    CAST(CASE WHEN DIR9_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR9_ROLE END AS VARCHAR(10)) AS DIR9_ROLE,
		------------------------------------- DIRECTOR 10 -----------------------------------------
		CAST(DIR10_GNDR AS VARCHAR(10)) AS DIR10_GNDR,
		CAST(DIR10_TITL AS VARCHAR(10)) AS DIR10_TITL,
		CAST(DIR10_FIRSTNAME AS VARCHAR(99)) AS DIR10_FIRSTNAME,
		CAST(DIR10_LASTNAME AS VARCHAR(99)) AS DIR10_LASTNAME,
		CAST(DIR10_FATHER_NAME AS VARCHAR(99)) AS DIR10_FATHER_NAME,
		CAST(DIR10_SSN_TYPE AS VARCHAR(10)) AS DIR10_SSN_TYPE,
		CAST(CASE WHEN DIR10_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR10_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR10_SSN,
	    CAST(DIR10_nationality1 AS VARCHAR(10)) AS DIR10_nationality1,
	    CAST(DIR10_Residence AS VARCHAR(10)) AS DIR10_Residence,
	    CAST(DIR10_tph_contact_type AS VARCHAR(10)) AS DIR10_tph_contact_type,
	    CAST(DIR10_tph_communication_type AS VARCHAR(10)) AS DIR10_tph_communication_type,
	    CAST(DIR10_tph_country_prefix AS VARCHAR(10)) AS DIR10_tph_country_prefix,
		CAST(DIR10_TPH_NUMBER AS VARCHAR(20)) AS DIR10_TPH_NUMBER,
		CAST(CASE WHEN DIR10_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR10_DATE_OF_BIRTH, 3) ELSE DIR10_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR10_DATE_OF_BIRTH,
	    CAST(DIR10_address_type AS VARCHAR(10)) AS DIR10_address_type,
		CAST(DIR10_ADDRESS AS VARCHAR(99)) AS DIR10_ADDRESS,
	    CAST(DIR10_CITY AS VARCHAR(20)) AS DIR10_CITY,
	    CAST(DIR10_country_code AS VARCHAR(10)) AS DIR10_country_code,
	    CAST(DIR10_STATE AS VARCHAR(20)) AS DIR10_STATE,
		CAST(DIR10_OCCUPATION AS VARCHAR(99)) AS DIR10_OCCUPATION,
	    CAST(CASE WHEN DIR10_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR10_ROLE END AS VARCHAR(10)) AS DIR10_ROLE,
		------------------------------------------------ TAX NUM --------------------------------------------------------
		CAST(TMC_TAX_NUM AS VARCHAR(99)) AS TTMC_TAX_NUM,
		--------------------------------------------- SIGNATORY 1 ----------------------------------------------------
	    CAST(SIGNATORY1_IS_PRIMARY AS VARCHAR(10)) AS SIGNATORY1_IS_PRIMARY,
		CAST(SIGNATORY1_GNDR AS VARCHAR(10)) AS SIGNATORY1_GNDR,
		CAST(SIGNATORY1_TITL AS VARCHAR(10)) AS SIGNATORY1_TITL,
		CAST(SIGNATORY1_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY1_FIRSTNAME,
		CAST(SIGNATORY1_LASTNAME AS VARCHAR(99)) AS SIGNATORY1_LASTNAME,
		CAST(SIGNATORY1_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY1_FATHER_NAME,
		CAST(SIGNATORY1_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY1_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY1_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY1_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY1_SSN,   
	    CAST(SIGNATORY1_nationality1 AS VARCHAR(10)) AS SIGNATORY1_nationality1,
	    CAST(SIGNATORY1_Residence AS VARCHAR(10)) AS SIGNATORY1_Residence,
	    CAST(SIGNATORY1_tph_contact_type AS VARCHAR(10)) AS SIGNATORY1_tph_contact_type,
	    CAST(SIGNATORY1_tph_communication_type AS VARCHAR(10)) AS SIGNATORY1_tph_communication_type,	
	    CAST(SIGNATORY1_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY1_tph_country_prefix,
		CAST(CASE WHEN SIGNATORY1_TPH_NUMBER IS NULL OR SIGNATORY1_TPH_NUMBER = '' THEN 
                  COALESCE(CASE WHEN DIR1_TPH_NUMBER IS NULL OR DIR1_TPH_NUMBER = '' THEN TTMC_tph_number END, DIR1_TPH_NUMBER ) ELSE SIGNATORY1_TPH_NUMBER END AS VARCHAR(50)) AS SIGNATORY1_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY1_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY1_DATE_OF_BIRTH, 3) ELSE SIGNATORY1_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY1_DATE_OF_BIRTH,
	    CAST(SIGNATORY1_address_type AS VARCHAR(20)) AS SIGNATORY1_address_type,
		CAST(SIGNATORY1_ADDRESS AS VARCHAR(99)) AS SIGNATORY1_ADDRESS,
	    CAST(SIGNATORY1_CITY AS VARCHAR(20)) AS SIGNATORY1_CITY,
	    CAST(SIGNATORY1_country_code AS VARCHAR(10)) AS SIGNATORY1_country_code,
	    CAST(SIGNATORY1_STATE AS VARCHAR(20)) AS SIGNATORY1_STATE,
		CAST(SIGNATORY1_OCCUPATION AS VARCHAR(99)) AS SIGNATORY1_OCCUPATION,
	    CAST(SIGNATORY1_ROLE AS VARCHAR(10)) AS SIGNATORY1_ROLE,
		--------------------------------------------- SIGNATORY 2 ----------------------------------------------------
	    CAST(CASE WHEN SIGNATORY2_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY2_IS_PRIMARY END AS VARCHAR(10)) AS SIGNATORY2_IS_PRIMARY,
		CAST(SIGNATORY2_GNDR AS VARCHAR(10)) AS SIGNATORY2_GNDR,
		CAST(SIGNATORY2_TITL AS VARCHAR(10)) AS SIGNATORY2_TITL,
		CAST(SIGNATORY2_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY2_FIRSTNAME,
		CAST(SIGNATORY2_LASTNAME AS VARCHAR(99)) AS SIGNATORY2_LASTNAME,
		CAST(SIGNATORY2_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY2_FATHER_NAME,
		CAST(SIGNATORY2_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY2_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY2_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY2_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY2_SSN,
	    CAST(SIGNATORY2_nationality1 AS VARCHAR(10)) AS SIGNATORY2_nationality1,
	    CAST(SIGNATORY2_Residence AS VARCHAR(10)) AS SIGNATORY2_Residence,
	    CAST(SIGNATORY2_tph_contact_type AS VARCHAR(10)) AS SIGNATORY2_tph_contact_type,
	    CAST(SIGNATORY2_tph_communication_type AS VARCHAR(10)) AS SIGNATORY2_tph_communication_type,	
	    CAST(SIGNATORY2_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY2_tph_country_prefix,
		CAST(SIGNATORY2_TPH_NUMBER AS VARCHAR(50)) AS SIGNATORY2_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY2_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY2_DATE_OF_BIRTH, 3) ELSE SIGNATORY2_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY2_DATE_OF_BIRTH,
	    CAST(SIGNATORY2_address_type AS VARCHAR(20)) AS SIGNATORY2_address_type,
		CAST(SIGNATORY2_ADDRESS AS VARCHAR(99)) AS SIGNATORY2_ADDRESS,
	    CAST(SIGNATORY2_CITY AS VARCHAR(20)) AS SIGNATORY2_CITY,
	    CAST(SIGNATORY2_country_code AS VARCHAR(10)) AS SIGNATORY2_country_code,
	    CAST(SIGNATORY2_STATE AS VARCHAR(20)) AS SIGNATORY2_STATE,
		CAST(SIGNATORY2_OCCUPATION AS VARCHAR(99)) AS SIGNATORY2_OCCUPATION,
	    CAST(CASE WHEN SIGNATORY2_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY2_ROLE END AS VARCHAR(10)) AS SIGNATORY2_ROLE,
        --------------------------------------------- SIGNATORY 3 ----------------------------------------------------
	    CAST(CASE WHEN SIGNATORY3_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY3_IS_PRIMARY END AS VARCHAR(10)) AS SIGNATORY3_IS_PRIMARY,
		CAST(SIGNATORY3_GNDR AS VARCHAR(10)) AS SIGNATORY3_GNDR,
		CAST(SIGNATORY3_TITL AS VARCHAR(10)) AS SIGNATORY3_TITL,
		CAST(SIGNATORY3_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY3_FIRSTNAME,
		CAST(SIGNATORY3_LASTNAME AS VARCHAR(99)) AS SIGNATORY3_LASTNAME,
		CAST(SIGNATORY3_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY3_FATHER_NAME,
		CAST(SIGNATORY3_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY3_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY3_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY3_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY3_SSN,
	    CAST(SIGNATORY3_nationality1 AS VARCHAR(10)) AS SIGNATORY3_nationality1,
	    CAST(SIGNATORY3_Residence AS VARCHAR(10)) AS SIGNATORY3_Residence,
	    CAST(SIGNATORY3_tph_contact_type AS VARCHAR(10)) AS SIGNATORY3_tph_contact_type,
	    CAST(SIGNATORY3_tph_communication_type AS VARCHAR(10)) AS SIGNATORY3_tph_communication_type,	
	    CAST(SIGNATORY3_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY3_tph_country_prefix,
		CAST(SIGNATORY3_TPH_NUMBER AS VARCHAR(50)) AS SIGNATORY3_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY3_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY3_DATE_OF_BIRTH, 3) ELSE SIGNATORY3_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY3_DATE_OF_BIRTH,
	    CAST(SIGNATORY3_address_type AS VARCHAR(20)) AS SIGNATORY3_address_type,
		CAST(SIGNATORY3_ADDRESS AS VARCHAR(99)) AS SIGNATORY3_ADDRESS,
	    CAST(SIGNATORY3_CITY AS VARCHAR(20)) AS SIGNATORY3_CITY,
	    CAST(SIGNATORY3_country_code AS VARCHAR(10)) AS SIGNATORY3_country_code,
	    CAST(SIGNATORY3_STATE AS VARCHAR(20)) AS SIGNATORY3_STATE,
		CAST(SIGNATORY3_OCCUPATION AS VARCHAR(99)) AS SIGNATORY3_OCCUPATION,
	    CAST(CASE WHEN SIGNATORY3_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY3_ROLE END AS VARCHAR(10)) AS SIGNATORY3_ROLE,
		--------------------------------------------- SIGNATORY 4 ----------------------------------------------------
	    CAST(CASE WHEN SIGNATORY4_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY4_IS_PRIMARY END AS VARCHAR(10)) AS SIGNATORY4_IS_PRIMARY,
		CAST(SIGNATORY4_GNDR AS VARCHAR(10)) AS SIGNATORY4_GNDR,
		CAST(SIGNATORY4_TITL AS VARCHAR(10)) AS SIGNATORY4_TITL,
		CAST(SIGNATORY4_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY4_FIRSTNAME,
		CAST(SIGNATORY4_LASTNAME AS VARCHAR(99)) AS SIGNATORY4_LASTNAME,
		CAST(SIGNATORY4_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY4_FATHER_NAME,
		CAST(SIGNATORY4_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY4_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY4_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY4_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY4_SSN,
	    CAST(SIGNATORY4_nationality1 AS VARCHAR(10)) AS SIGNATORY4_nationality1,
	    CAST(SIGNATORY4_Residence AS VARCHAR(10)) AS SIGNATORY4_Residence,
	    CAST(SIGNATORY4_tph_contact_type AS VARCHAR(10)) AS SIGNATORY4_tph_contact_type,
	    CAST(SIGNATORY4_tph_communication_type AS VARCHAR(10)) AS SIGNATORY4_tph_communication_type,	
	    CAST(SIGNATORY4_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY4_tph_country_prefix,
		CAST(SIGNATORY4_TPH_NUMBER AS VARCHAR(50)) AS SIGNATORY4_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY4_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY4_DATE_OF_BIRTH, 3) ELSE SIGNATORY4_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY4_DATE_OF_BIRTH,
	    CAST(SIGNATORY4_address_type AS VARCHAR(20)) AS SIGNATORY4_address_type,
		CAST(SIGNATORY4_ADDRESS AS VARCHAR(99)) AS SIGNATORY4_ADDRESS,
	    CAST(SIGNATORY4_CITY AS VARCHAR(20)) AS SIGNATORY4_CITY,
	    CAST(SIGNATORY4_country_code AS VARCHAR(10)) AS SIGNATORY4_country_code,
	    CAST(SIGNATORY4_STATE AS VARCHAR(20)) AS SIGNATORY4_STATE,
		CAST(SIGNATORY4_OCCUPATION AS VARCHAR(99)) AS SIGNATORY4_OCCUPATION,
	    CAST(CASE WHEN SIGNATORY4_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY4_ROLE END AS VARCHAR(10)) AS SIGNATORY4_ROLE,
		--------------------------------------------- SIGNATORY 5 ----------------------------------------------------
	    CAST(CASE WHEN SIGNATORY5_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY5_IS_PRIMARY END AS VARCHAR(10)) AS SIGNATORY5_IS_PRIMARY,
		CAST(SIGNATORY5_GNDR AS VARCHAR(10)) AS SIGNATORY5_GNDR,
		CAST(SIGNATORY5_TITL AS VARCHAR(10)) AS SIGNATORY5_TITL,
		CAST(SIGNATORY5_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY5_FIRSTNAME,
		CAST(SIGNATORY5_LASTNAME AS VARCHAR(99)) AS SIGNATORY5_LASTNAME,
		CAST(SIGNATORY5_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY5_FATHER_NAME,
		CAST(SIGNATORY5_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY5_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY5_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY5_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY5_SSN,
	    CAST(SIGNATORY5_nationality1 AS VARCHAR(10)) AS SIGNATORY5_nationality1,
	    CAST(SIGNATORY5_Residence AS VARCHAR(10)) AS SIGNATORY5_Residence,
	    CAST(SIGNATORY5_tph_contact_type AS VARCHAR(10)) AS SIGNATORY5_tph_contact_type,
	    CAST(SIGNATORY5_tph_communication_type AS VARCHAR(10)) AS SIGNATORY5_tph_communication_type,	
	    CAST(SIGNATORY5_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY5_tph_country_prefix,
		CAST(SIGNATORY5_TPH_NUMBER AS VARCHAR(50)) AS SIGNATORY5_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY5_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY5_DATE_OF_BIRTH, 3) ELSE SIGNATORY5_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY5_DATE_OF_BIRTH,
	    CAST(SIGNATORY5_address_type AS VARCHAR(20)) AS SIGNATORY5_address_type,
		CAST(SIGNATORY5_ADDRESS AS VARCHAR(99)) AS SIGNATORY5_ADDRESS,
	    CAST(SIGNATORY5_CITY AS VARCHAR(20)) AS SIGNATORY5_CITY,
	    CAST(SIGNATORY5_country_code AS VARCHAR(10)) AS SIGNATORY5_country_code,
	    CAST(SIGNATORY5_STATE AS VARCHAR(20)) AS SIGNATORY5_STATE,
		CAST(SIGNATORY5_OCCUPATION AS VARCHAR(99)) AS SIGNATORY5_OCCUPATION,
	    CAST(CASE WHEN SIGNATORY5_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY5_ROLE END AS VARCHAR(10)) AS SIGNATORY5_ROLE,
		--------------------------------------------- SIGNATORY 6 ----------------------------------------------------
	    CAST(CASE WHEN SIGNATORY6_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY6_IS_PRIMARY END AS VARCHAR(10)) AS SIGNATORY6_IS_PRIMARY,
		CAST(SIGNATORY6_GNDR AS VARCHAR(10)) AS SIGNATORY6_GNDR,
		CAST(SIGNATORY6_TITL AS VARCHAR(10)) AS SIGNATORY6_TITL,
		CAST(SIGNATORY6_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY6_FIRSTNAME,
		CAST(SIGNATORY6_LASTNAME AS VARCHAR(99)) AS SIGNATORY6_LASTNAME,
		CAST(SIGNATORY6_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY6_FATHER_NAME,
		CAST(SIGNATORY6_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY6_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY6_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY6_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY6_SSN,
	    CAST(SIGNATORY6_nationality1 AS VARCHAR(10)) AS SIGNATORY6_nationality1,
	    CAST(SIGNATORY6_Residence AS VARCHAR(10)) AS SIGNATORY6_Residence,
	    CAST(SIGNATORY6_tph_contact_type AS VARCHAR(10)) AS SIGNATORY6_tph_contact_type,
	    CAST(SIGNATORY6_tph_communication_type AS VARCHAR(10)) AS SIGNATORY6_tph_communication_type,	
	    CAST(SIGNATORY6_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY6_tph_country_prefix,
		CAST(SIGNATORY6_TPH_NUMBER AS VARCHAR(50)) AS SIGNATORY6_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY6_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY6_DATE_OF_BIRTH, 3) ELSE SIGNATORY6_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY6_DATE_OF_BIRTH,
	    CAST(SIGNATORY6_address_type AS VARCHAR(20)) AS SIGNATORY6_address_type,
		CAST(SIGNATORY6_ADDRESS AS VARCHAR(99)) AS SIGNATORY6_ADDRESS,
	    CAST(SIGNATORY6_CITY AS VARCHAR(20)) AS SIGNATORY6_CITY,
	    CAST(SIGNATORY6_country_code AS VARCHAR(10)) AS SIGNATORY6_country_code,
	    CAST(SIGNATORY6_STATE AS VARCHAR(20)) AS SIGNATORY6_STATE,
		CAST(SIGNATORY6_OCCUPATION AS VARCHAR(99)) AS SIGNATORY6_OCCUPATION,
	    CAST(CASE WHEN SIGNATORY6_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY6_ROLE END AS VARCHAR(10)) AS SIGNATORY6_ROLE,
		--------------------------------------------- SIGNATORY 7 ----------------------------------------------------
	    CAST(CASE WHEN SIGNATORY7_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY7_IS_PRIMARY END AS VARCHAR(10)) AS SIGNATORY7_IS_PRIMARY,
		CAST(SIGNATORY7_GNDR AS VARCHAR(10)) AS SIGNATORY7_GNDR,
		CAST(SIGNATORY7_TITL AS VARCHAR(10)) AS SIGNATORY7_TITL,
		CAST(SIGNATORY7_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY7_FIRSTNAME,
		CAST(SIGNATORY7_LASTNAME AS VARCHAR(99)) AS SIGNATORY7_LASTNAME,
		CAST(SIGNATORY7_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY7_FATHER_NAME,
		CAST(SIGNATORY7_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY7_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY7_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY7_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY7_SSN,
	    CAST(SIGNATORY7_nationality1 AS VARCHAR(10)) AS SIGNATORY7_nationality1,
	    CAST(SIGNATORY7_Residence AS VARCHAR(10)) AS SIGNATORY7_Residence,
	    CAST(SIGNATORY7_tph_contact_type AS VARCHAR(10)) AS SIGNATORY7_tph_contact_type,
	    CAST(SIGNATORY7_tph_communication_type AS VARCHAR(10)) AS SIGNATORY7_tph_communication_type,	
	    CAST(SIGNATORY7_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY7_tph_country_prefix,
		CAST(SIGNATORY7_TPH_NUMBER AS VARCHAR(50)) AS SIGNATORY7_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY7_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY7_DATE_OF_BIRTH, 3) ELSE SIGNATORY7_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY7_DATE_OF_BIRTH,
	    CAST(SIGNATORY7_address_type AS VARCHAR(20)) AS SIGNATORY7_address_type,
		CAST(SIGNATORY7_ADDRESS AS VARCHAR(99)) AS SIGNATORY7_ADDRESS,
	    CAST(SIGNATORY7_CITY AS VARCHAR(20)) AS SIGNATORY7_CITY,
	    CAST(SIGNATORY7_country_code AS VARCHAR(10)) AS SIGNATORY7_country_code,
	    CAST(SIGNATORY7_STATE AS VARCHAR(20)) AS SIGNATORY7_STATE,
		CAST(SIGNATORY7_OCCUPATION AS VARCHAR(99)) AS SIGNATORY7_OCCUPATION,
	    CAST(CASE WHEN SIGNATORY7_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY7_ROLE END AS VARCHAR(10)) AS SIGNATORY7_ROLE,
		--------------------------------------------- SIGNATORY 8 ----------------------------------------------------
	    CAST(CASE WHEN SIGNATORY8_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY8_IS_PRIMARY END AS VARCHAR(10)) AS SIGNATORY8_IS_PRIMARY,
		CAST(SIGNATORY8_GNDR AS VARCHAR(10)) AS SIGNATORY8_GNDR,
		CAST(SIGNATORY8_TITL AS VARCHAR(10)) AS SIGNATORY8_TITL,
		CAST(SIGNATORY8_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY8_FIRSTNAME,
		CAST(SIGNATORY8_LASTNAME AS VARCHAR(99)) AS SIGNATORY8_LASTNAME,
		CAST(SIGNATORY8_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY8_FATHER_NAME,
		CAST(SIGNATORY8_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY8_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY8_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY8_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY8_SSN,
	    CAST(SIGNATORY8_nationality1 AS VARCHAR(10)) AS SIGNATORY8_nationality1,
	    CAST(SIGNATORY8_Residence AS VARCHAR(10)) AS SIGNATORY8_Residence,
	    CAST(SIGNATORY8_tph_contact_type AS VARCHAR(10)) AS SIGNATORY8_tph_contact_type,
	    CAST(SIGNATORY8_tph_communication_type AS VARCHAR(10)) AS SIGNATORY8_tph_communication_type,	
	    CAST(SIGNATORY8_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY8_tph_country_prefix,
		CAST(SIGNATORY8_TPH_NUMBER AS VARCHAR(50)) AS SIGNATORY8_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY8_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY8_DATE_OF_BIRTH, 3) ELSE SIGNATORY8_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY8_DATE_OF_BIRTH,
	    CAST(SIGNATORY8_address_type AS VARCHAR(20)) AS SIGNATORY8_address_type,
		CAST(SIGNATORY8_ADDRESS AS VARCHAR(99)) AS SIGNATORY8_ADDRESS,
	    CAST(SIGNATORY8_CITY AS VARCHAR(20)) AS SIGNATORY8_CITY,
	    CAST(SIGNATORY8_country_code AS VARCHAR(10)) AS SIGNATORY8_country_code,
	    CAST(SIGNATORY8_STATE AS VARCHAR(20)) AS SIGNATORY8_STATE,
		CAST(SIGNATORY8_OCCUPATION AS VARCHAR(99)) AS SIGNATORY8_OCCUPATION,
	    CAST(CASE WHEN SIGNATORY8_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY8_ROLE END AS VARCHAR(10)) AS SIGNATORY8_ROLE,

		CAST(TTMC_open AS VARCHAR(20)) AS TTMC_open,
		CAST(TTMC_status_code AS VARCHAR(10)) AS TTMC_status_code,
		CAST(TTMC_to_country AS VARCHAR(10)) AS TTMC_to_country
		FROM Final_Chunk 
		)


	  	SELECT * FROM DATA_V1
	  	WHERE CATEGORY = '{entity_individual_flag}' ;"""
    	
		
	return query


def get_cash_deposit_query_v2(trxn_date, entity_individual_flag):
	query = rf"""

		WITH ENTITY AS (
		SELECT
		FCT.TSACTN_ID,
		FCT.ACCT_SROGT_ID
		FROM DP_SDMVW_DFDN.FCT_RTAIL_BNK_TSACTN_VW FCT
		INNER JOIN DP_SDMVW_DFDN.DIM_RTAIL_BNK_ACCT_VW ACCT ON ACCT.ACCT_SROGT_ID = FCT.ACCT_SROGT_ID
		LEFT JOIN (select CURY_EDW_ID, EXCH_RATE as CCY_RATE FROM  DP_SDMVW_DFDN.FCT_CURY_EXCH_RATE_VW where BATCH_DT = '{trxn_date}')
		EXC
		ON FCT.CURY_EDW_ID = EXC.CURY_EDW_ID
		WHERE 1=1
		--AND ACCT.ACCT_SROGT_ID IN ('255285915')
		--AND FCT.TSACTN_ID IN ('6576257638')
		AND FCT.TSACTN_TYPE_EDW_ID IN ('0001','0201','0006')
		AND FCT.TSACTN_DT = '{trxn_date}'
		AND CASE WHEN EXC.CURY_EDW_ID IS NOT NULL THEN FCT.TSACTN_AMT * CCY_RATE ELSE FCT.TSACTN_AMT END >= '2000000'
		AND 
		( 
		ACCT.CUST_TYPE_EDW_ID IN ( '63','51','36','31','61','34','53','37','35','65','33','32','55','62','64','54','52') 
		OR
		EXISTS(
		SELECT 1 FROM DP_SDMVW_DFDN.DIM_CTR_Keywords_VW t 
		WHERE t.flag = 'NO' AND ACCT.ACCT_TITL LIKE '%' || t.keyword || '%'
		)
		OR 
		EXISTS(
		SELECT 1 FROM DP_SDMVW_DFDN.DIM_CTR_Keywords_VW t 
		WHERE t.flag = 'YES' AND REGEXP_INSTR(ACCT.ACCT_TITL, '(^|[^A-Z0-9])' || t.keyword || '([^A-Z0-9]|$)', 1,1,0, 'i') > 0
		)
		)
		AND FCT.CR_DR_IND = 'C'
		AND FCT.RVSL_SEQ_NUM IS NULL
		AND FCT.Reveral_IND = 'N'
		AND FCT.TRAC_ID IS NULL
		)

		,TRXNS AS (
		SELECT
		FCT.*, 
		CASE WHEN FCT.CURY_EDW_ID <> 'PKR' THEN FCT.CURY_EDW_ID ELSE CAST(NULL AS VARCHAR(10)) END AS FRGN_CCY,
		CASE WHEN FCT.CURY_EDW_ID <> 'PKR' THEN CAST(FCT.TSACTN_AMT AS INT) ELSE CAST(NULL AS VARCHAR(10)) END AS FRGN_TSACTN_AMT,
		CASE WHEN FCT.CURY_EDW_ID <> 'PKR' THEN EXC.CCY_RATE ELSE CAST(NULL AS VARCHAR(10)) END AS EXCHANGE_RATE,
		FCT.TSACTN_AMT * EXC.CCY_RATE AS FRGN_TSACTN_AMT_PKR,
		ACCT.JOIN_ACCT_FLG,
		ACCT.ACCT_TITL,
		ACCT.ACCT_SROGT_ID AS ACCOUNT_SROGT_ID, ACCT.CUST_TYPE_EDW_ID AS ACCOUNT_CUST_TYPE_EDW_ID , ACCT.CUST_SROGT_ID AS ACCT_CUST_SROGT_ID, ACCT.BRNCH_SROGT_ID AS ACCT_BRNCH_SROGT_ID ,
		ACCT.ACCT_ORIGNL_OPN_DT , ACCT.ACCT_DESC, ACCT.CURY_EDW_ID AS ACCT_CURY_EDW_ID,
		PROD.ACCT_TYPE_DESC,
		--PROD.CODE AS ACCT_TYPE_CODE ,
		CASE WHEN REGEXP_SIMILAR(UPPER(ACCT.ACCT_TITL), '.*(^|[^A-Z0-9])CDC([^A-Z0-9]|$).*') = 1 THEN 'ATSAV' ELSE PROD.CODE END AS ACCT_TYPE_CODE,
		COD.CATEGORY_TYPE_DESC,
		COD.CODE AS CATEGORY_TYPE_CODE,
		CASE WHEN E.ACCT_SROGT_ID IS NOT NULL THEN 'ENTITY' ELSE 'INDIVIDUAL' END AS CATEGORY
		
		FROM DP_SDMVW_DFDN.FCT_RTAIL_BNK_TSACTN_VW FCT
		INNER JOIN DP_SDMVW_DFDN.DIM_RTAIL_BNK_ACCT_VW ACCT ON ACCT.ACCT_SROGT_ID = FCT.ACCT_SROGT_ID
		LEFT JOIN ENTITY E ON FCT.TSACTN_ID = E.TSACTN_ID 
		LEFT JOIN DP_SDMT_DFDN.DIM_CTR_ACCT_TYPE prod ON ACCT.PROD_SROGT_ID = prod.ACCT_TYPE 
		LEFT JOIN DP_SDMT_DFDN.DIM_CTR_CATEGORY_CODES COD ON ACCT.CUST_TYPE_EDW_ID = COD.CATEGORY_TYPE
		LEFT JOIN (select CURY_EDW_ID, EXCH_RATE as CCY_RATE FROM  DP_SDMVW_DFDN.FCT_CURY_EXCH_RATE_VW where BATCH_DT = '{trxn_date}') EXC
		ON FCT.CURY_EDW_ID = EXC.CURY_EDW_ID
		WHERE 1=1
		--AND ACCT.ACCT_SROGT_ID IN ('255285915')
		--AND FCT.TSACTN_ID IN ('6576257638')
		AND FCT.TSACTN_TYPE_EDW_ID IN ('0001','0201','0006')
		AND FCT.TSACTN_DT = '{trxn_date}'
		AND CASE WHEN EXC.CURY_EDW_ID IS NOT NULL THEN FCT.TSACTN_AMT * CCY_RATE ELSE FCT.TSACTN_AMT END >= '2000000'
		AND FCT.CR_DR_IND = 'C'
		AND FCT.RVSL_SEQ_NUM IS NULL
		AND FCT.Reveral_IND = 'N'
		AND FCT.TRAC_ID IS NULL
		)
		
		-- DP_REPORTING_MART.TM_DM_MD_MANDATE_AUTHORIZE
		, ENTITY_SIGNATORY AS (
		SELECT x.*,
	    ROW_NUMBER() OVER(PARTITION BY ACCT_SROGT_ID ORDER BY M_DT_OF_BIRTH DESC) AS M_RN
	    FROM (
			SELECT
			    T.ACCT_SROGT_ID,
			    T.TSACTN_ID,
			    M.CLIENT_NO AS M_CLIENT_NO,
				'TRUE' AS M_IS_PRIMARY, 
				CASE 
					 WHEN MC.GNDR IS NOT NULL THEN MC.GNDR
					 WHEN MC.GNDR IS NULL THEN 
								CASE WHEN RIGHT(MC.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(MC.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'M' 
								WHEN RIGHT(MC.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(MC.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'F' 
								ELSE CAST(NULL AS VARCHAR(10)) END END AS M_GNDR,			
				CASE 
					 WHEN MC.TITL IS NOT NULL THEN MC.TITL
					 WHEN MC.TITL IS NULL THEN 
								CASE WHEN RIGHT(MC.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(MC.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'MR' 
								WHEN RIGHT(MC.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(MC.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'MS'
								ELSE CAST(NULL AS VARCHAR(10)) END END AS M_TITL, 			

			    TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
						FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) )  AS  M_FRST_NAME,
				
				CASE WHEN  REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0 
							THEN  TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
				              			  POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) )
							ELSE 
									CASE WHEN (MC.FRST_NAME IS NULL AND MC.MDL_NAME IS NULL AND MC.LAST_NAME IS NULL) OR (MC.FRST_NAME = '' AND MC.MDL_NAME = '' AND MC.LAST_NAME = '')
												THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
												 			FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
												ELSE 
														CASE WHEN REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(MC.FRST_NAME, '') || ' ' || COALESCE(MC.MDL_NAME, '') || ' ' || COALESCE(MC.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0
																	THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(MC.FRST_NAME, '') || ' ' || COALESCE(MC.MDL_NAME, '') || ' ' || COALESCE(MC.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
													            				POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(MC.FRST_NAME, '') || ' ' || COALESCE(MC.MDL_NAME, '') || ' ' || COALESCE(MC.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) 
														ELSE TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
																 	FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
														END
									END
				END	AS M_LAST_NAME ,
				
			    TO_CHAR(MC.DT_OF_BIRTH , 'YYYY-MM-DD') ||  'T00:00:00' AS M_DT_OF_BIRTH,
				TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.FTHR_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) AS M_MOTHER_NAME,
				
				MC.IDNTFTN_TYPE_EDW_ID AS M_SSN_TYPE,
				CASE WHEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) = '' THEN CAST(NULL AS VARCHAR(10)) 
							   ELSE TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) END AS M_SSN,
			     CASE
					when MC.MBL_NUM is not null AND MC.MBL_NUM <> ''  
					THEN REGEXP_REPLACE(REGEXP_REPLACE(TRIM(MC.MBL_NUM), '[^0-9]', ''), '^(0092|[+]92|92|0)+', '')
			        when MC.PHN_RSDNC is not null AND MC.PHN_RSDNC <> '' then TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(MC.PHN_RSDNC), '[^ ]+', 1, 1), '[^0-9]', '') )
			        else 
					case 
						WHEN REGEXP_SIMILAR(MC.PHN_BUSN, '.*[A-Za-z].*') = '1' AND REGEXP_SIMILAR(MC.PHN_BUSN, '.*[0-9].*') = '1' THEN CAST(NULL AS VARCHAR(11))
						WHEN REGEXP_SIMILAR(MC.PHN_BUSN, '.*[A-Za-z].*') = '1' THEN CAST(NULL AS VARCHAR(11))
						ELSE 
							case
								when substr(regexp_replace(MC.PHN_BUSN, '[^0-9]', ''), 1,3) = '092' then substr(regexp_replace(MC.PHN_BUSN, '[^0-9]', ''), 3) 
								when substr(regexp_replace(MC.PHN_BUSN, '[^0-9]', ''), 1,2) = '92' then substr(regexp_replace(MC.PHN_BUSN, '[^0-9]', ''), 3)  
								ELSE trim(LEADING '0' FROM regexp_replace(MC.PHN_BUSN, '[^0-9]', ''))
							end
					end 
				END as M_tph_number,      	
				
				TRIM(OREPLACE(OREPLACE(
				CASE 
				WHEN TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is not null AND TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3
				              THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' ')  , '[[:space:]]+', ' '))  
				WHEN (TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
						       AND (TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
						      THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' ')) 
				WHEN (TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
						       AND ( TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(MC.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))
				WHEN (TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3 ) 
						       AND (TRIM(REGEXP_REPLACE(TRIM(MC.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(MC.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.OTH_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(MC.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))		   
				ELSE CAST(NULL AS VARCHAR(10)) 
				END
				,CHR(13),' '),CHR(10), ' ')) as M_address,

			    CASE WHEN _MDO.OCPTN_DESC IS NOT NULL OR _MDO.OCPTN_DESC <> '' THEN _MDO.OCPTN_DESC ELSE 'Others' END AS M_OCCUPATION,
				
				MC.CTRY_OF_NTLTY as M_nationality1,
				'PK' as M_Residence,
				CASE WHEN MC.MBL_NUM is not null AND MC.MBL_NUM <> '' then 'PAPVT' when MC.MBL_NUM is null OR MC.MBL_NUM = '' then 'PAOFF' END as M_tph_contact_type,
				CASE WHEN MC.MBL_NUM is not null AND MC.MBL_NUM <> '' then 'COMOB' else 'COLAN' END as M_tph_communication_type,
				'92' as M_tph_country_prefix,
				
				CASE WHEN MC.PERM_ADDR is not null and MC.PERM_ADDR <> '' then 'PAPVT' 
							when MC.PERM_ADDR is null OR MC.PERM_ADDR = '' then 'PAOFF' END as M_address_type,
							
				CASE WHEN TRIM(MC.RSDNTL_CITY)  = '0' THEN CAST(NULL AS VARCHAR(10)) ELSE MC.RSDNTL_CITY END AS M_city, 
				
				'PK' as M_country_code,
				CASE  
				when substr(MC.IDNTFTN_VAL,1,1) IN ('1', '2') then 'KHYBER-PAKHTUNKHWA'
				when substr(MC.IDNTFTN_VAL,1,1) IN ('3', '6') then 'PUNJAB'
				when substr(MC.IDNTFTN_VAL,1,1) = '4' then 'SINDH'
				when substr(MC.IDNTFTN_VAL,1,1) = '5' then 'BALOCHISTAN'
				when substr(MC.IDNTFTN_VAL,1,1) = '7' then 'GILGIT-BALISTAN'
				when substr(MC.IDNTFTN_VAL,1,1) = '8' then 'AZAD-KASHMIR'
				ELSE cast(null as varchar(10)) 
				END as M_state,
				
				'ARPYS' AS M_role
				
			    ,ROW_NUMBER() OVER(PARTITION BY M.CLIENT_NO ORDER BY M.CLIENT_NO) AS RN
		    FROM  TRXNS T
		    INNER JOIN DP_REPORTING_MART.TM_DM_MD_MANDATE_AUTHORIZE M ON T.ACCT_SROGT_ID = M.ACCT_NO  -- DP_SDMVW_DFDN.TM_DM_MD_MANDATE_AUTHORIZE_VW 
		    LEFT JOIN DP_SDMVW_DFDN.DIM_CUST_VW MC ON MC.CUST_SROGT_ID = M.CLIENT_NO AND MC.SYSTEM_CODE = 'CBS'
		    LEFT JOIN DP_SDMT_DFDN.DIM_OCPTN_SS _MDO ON MC.OCPTN_EDW_ID = _MDO.OCPTN_EDW_ID
		    WHERE 1=1 AND M.START_DATE = (SELECT CAST(MAX(START_DATE) AS DATE) AS START_DATE FROM DP_REPORTING_MART.TM_DM_MD_MANDATE_AUTHORIZE)
			 -- CAST(CURRENT_DATE - 1 AS DATE)
			 AND T.CATEGORY = 'ENTITY'
			
	    ) AS X
	    WHERE 1=1
	  	AND X.RN = 1
		)
		
		, INDIVIDUAL_ACCTS_CUSTOMERS AS ( 
			SELECT DISTINCT
			T.ACCT_SROGT_ID, T.ACCT_CUST_SROGT_ID, T.JOIN_ACCT_FLG
			FROM TRXNS T -- DT_SDMT_UBL.CTR_TRXNS T
			WHERE 1=1 
			AND T.CATEGORY = 'INDIVIDUAL'

			UNION ALL

			SELECT DISTINCT
			T.ACCT_SROGT_ID, J.CUST_SROGT_ID AS ACCT_CUST_SROGT_ID , T.JOIN_ACCT_FLG
			FROM TRXNS T --DT_SDMT_UBL.CTR_TRXNS  T
			INNER JOIN DP_SDMT_DFDN.DIM_RTAIL_BNK_ACCT_JNT J ON T.ACCT_SROGT_ID = J.ACCT_SROGT_ID AND T.JOIN_ACCT_FLG = 1
			WHERE 1=1
			AND T.CATEGORY = 'INDIVIDUAL'
			)
		
		, INDIVIDUAL_SIGNATORY AS (
			SELECT DISTINCT 
		    T.ACCT_SROGT_ID,
			--T.ACCT_TITL,
		    T.TSACTN_ID,
		    M.ACCT_CUST_SROGT_ID AS M_CLIENT_NO,
			-- T.JOIN_ACCT_FLG,
			'TRUE' AS M_IS_PRIMARY, 
			CASE 
				 WHEN MC.GNDR IS NOT NULL THEN MC.GNDR
				 WHEN MC.GNDR IS NULL THEN 
							CASE WHEN RIGHT(MC.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(MC.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'M' 
							WHEN RIGHT(MC.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(MC.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'F' 
							ELSE CAST(NULL AS VARCHAR(10)) END END AS M_GNDR,			
			CASE 
				 WHEN MC.TITL IS NOT NULL THEN MC.TITL
				 WHEN MC.TITL IS NULL THEN 
							CASE WHEN RIGHT(MC.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(MC.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'MR' 
							WHEN RIGHT(MC.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(MC.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'MS'
							ELSE CAST(NULL AS VARCHAR(10)) END END AS M_TITL, 			

		    TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
					FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) )  AS  M_FRST_NAME,
			
			CASE WHEN  REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0 
						THEN  TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
			              			  POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) )
						ELSE 
								CASE WHEN (MC.FRST_NAME IS NULL AND MC.MDL_NAME IS NULL AND MC.LAST_NAME IS NULL) OR (MC.FRST_NAME = '' AND MC.MDL_NAME = '' AND MC.LAST_NAME = '')
											THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
											 			FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
											ELSE 
													CASE WHEN REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(MC.FRST_NAME, '') || ' ' || COALESCE(MC.MDL_NAME, '') || ' ' || COALESCE(MC.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0
																THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(MC.FRST_NAME, '') || ' ' || COALESCE(MC.MDL_NAME, '') || ' ' || COALESCE(MC.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
												            				POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(MC.FRST_NAME, '') || ' ' || COALESCE(MC.MDL_NAME, '') || ' ' || COALESCE(MC.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) 
													ELSE TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
															 	FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
													END
								END
			END	AS M_LAST_NAME ,
			
		    TO_CHAR(MC.DT_OF_BIRTH , 'YYYY-MM-DD') ||  'T00:00:00' AS M_DT_OF_BIRTH,
			TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.FTHR_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) AS M_MOTHER_NAME,
			
			MC.IDNTFTN_TYPE_EDW_ID AS M_SSN_TYPE,
			CASE WHEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) = '' THEN CAST(NULL AS VARCHAR(10)) 
						   ELSE TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) END AS M_SSN,
		     CASE
				when MC.MBL_NUM is not null AND MC.MBL_NUM <> ''  
				THEN REGEXP_REPLACE(REGEXP_REPLACE(TRIM(MC.MBL_NUM), '[^0-9]', ''), '^(0092|[+]92|92|0)+', '')
		        when MC.PHN_RSDNC is not null AND MC.PHN_RSDNC <> '' then TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(MC.PHN_RSDNC), '[^ ]+', 1, 1), '[^0-9]', '') )
		        else 
				case 
					WHEN REGEXP_SIMILAR(MC.PHN_BUSN, '.*[A-Za-z].*') = '1' AND REGEXP_SIMILAR(MC.PHN_BUSN, '.*[0-9].*') = '1' THEN CAST(NULL AS VARCHAR(11))
					WHEN REGEXP_SIMILAR(MC.PHN_BUSN, '.*[A-Za-z].*') = '1' THEN CAST(NULL AS VARCHAR(11))
					ELSE 
						case
							when substr(regexp_replace(MC.PHN_BUSN, '[^0-9]', ''), 1,3) = '092' then substr(regexp_replace(MC.PHN_BUSN, '[^0-9]', ''), 3) 
							when substr(regexp_replace(MC.PHN_BUSN, '[^0-9]', ''), 1,2) = '92' then substr(regexp_replace(MC.PHN_BUSN, '[^0-9]', ''), 3)  
							ELSE trim(LEADING '0' FROM regexp_replace(MC.PHN_BUSN, '[^0-9]', ''))
						end
				end 
			END as M_tph_number,      	
			
			TRIM(OREPLACE(OREPLACE(
			CASE 
			WHEN TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is not null AND TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3
			              THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' ')  , '[[:space:]]+', ' '))  
			WHEN (TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
					       AND (TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
					      THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' ')) 
			WHEN (TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
					       AND ( TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
						   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(MC.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))
			WHEN (TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3 ) 
					       AND (TRIM(REGEXP_REPLACE(TRIM(MC.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(MC.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.OTH_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
						   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(MC.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))		   
			ELSE CAST(NULL AS VARCHAR(10)) 
			END
			,CHR(13),' '),CHR(10), ' ')) as M_address,

		    CASE WHEN _MDO.OCPTN_DESC IS NOT NULL OR _MDO.OCPTN_DESC <> '' THEN _MDO.OCPTN_DESC ELSE 'Others' END AS M_OCCUPATION,
			
			MC.CTRY_OF_NTLTY as M_nationality1,
			'PK' as M_Residence,
			CASE WHEN MC.MBL_NUM is not null AND MC.MBL_NUM <> '' then 'PAPVT' when MC.MBL_NUM is null OR MC.MBL_NUM = '' then 'PAOFF' END as M_tph_contact_type,
			CASE WHEN MC.MBL_NUM is not null AND MC.MBL_NUM <> '' then 'COMOB' else 'COLAN' END as M_tph_communication_type,
			'92' as M_tph_country_prefix,
			
			CASE WHEN MC.PERM_ADDR is not null and MC.PERM_ADDR <> '' then 'PAPVT' 
						when MC.PERM_ADDR is null OR MC.PERM_ADDR = '' then 'PAOFF' END as M_address_type,
						
			CASE WHEN TRIM(MC.RSDNTL_CITY)  = '0' THEN CAST(NULL AS VARCHAR(10)) ELSE MC.RSDNTL_CITY END AS M_city, 
			
			'PK' as M_country_code,
			CASE  
			when substr(MC.IDNTFTN_VAL,1,1) IN ('1', '2') then 'KHYBER-PAKHTUNKHWA'
			when substr(MC.IDNTFTN_VAL,1,1) IN ('3', '6') then 'PUNJAB'
			when substr(MC.IDNTFTN_VAL,1,1) = '4' then 'SINDH'
			when substr(MC.IDNTFTN_VAL,1,1) = '5' then 'BALOCHISTAN'
			when substr(MC.IDNTFTN_VAL,1,1) = '7' then 'GILGIT-BALISTAN'
			when substr(MC.IDNTFTN_VAL,1,1) = '8' then 'AZAD-KASHMIR'
			ELSE cast(null as varchar(10)) 
			END as M_state,
			
			'ARPYS' AS M_role
			
		    -- ,ROW_NUMBER() OVER(PARTITION BY M.CLIENT_NO ORDER BY M.CLIENT_NO) AS RN
	    FROM  TRXNS T --DT_SDMT_UBL.CTR_TRXNS T
	    INNER JOIN INDIVIDUAL_ACCTS_CUSTOMERS M ON T.ACCT_SROGT_ID = M.ACCT_SROGT_ID  -- DP_SDMVW_DFDN.TM_DM_MD_MANDATE_AUTHORIZE_VW 
	    LEFT JOIN DP_SDMVW_DFDN.DIM_CUST_VW MC ON MC.CUST_SROGT_ID = M.ACCT_CUST_SROGT_ID AND MC.SYSTEM_CODE = 'CBS'
	    LEFT JOIN DP_SDMT_DFDN.DIM_OCPTN_SS _MDO ON MC.OCPTN_EDW_ID = _MDO.OCPTN_EDW_ID
		)
		
		
		, MANDATE AS (
		SELECT X.*,
		ROW_NUMBER() OVER(PARTITION BY ACCT_SROGT_ID ORDER BY M_DT_OF_BIRTH DESC) AS M_RN
		FROM (
				SELECT ACCT_SROGT_ID, /*TSACTN_ID,*/  M_CLIENT_NO, M_IS_PRIMARY, M_GNDR, M_TITL, M_FRST_NAME,
					M_LAST_NAME, M_DT_OF_BIRTH, M_MOTHER_NAME, M_SSN_TYPE, M_SSN, M_tph_number, M_address,
					M_OCCUPATION, M_nationality1, M_Residence, M_tph_contact_type, M_tph_communication_type, 
					M_tph_country_prefix, M_address_type, M_city, M_country_code, M_state, M_role
				FROM ENTITY_SIGNATORY
				UNION 
				SELECT ACCT_SROGT_ID, /*TSACTN_ID,*/  M_CLIENT_NO, M_IS_PRIMARY, M_GNDR, M_TITL, M_FRST_NAME,
					M_LAST_NAME, M_DT_OF_BIRTH, M_MOTHER_NAME, M_SSN_TYPE, M_SSN, M_tph_number, M_address,
					M_OCCUPATION, M_nationality1, M_Residence, M_tph_contact_type, M_tph_communication_type, 
					M_tph_country_prefix, M_address_type, M_city, M_country_code, M_state, M_role
				FROM INDIVIDUAL_SIGNATORY
		 ) AS X
		 )
		 
			 
		 	-- DP_REPORTING_MART.FM_DIRECTOR_DTLS
		, DIRECTORS AS (
		SELECT x.*, ROW_NUMBER() OVER(PARTITION BY CUST_SROGT_ID ORDER BY D_DT_OF_BIRTH DESC) AS D_RN
		FROM (
			SELECT 
				T.ACCT_SROGT_ID,
				T.CUST_SROGT_ID,
				T.TSACTN_ID,
				DC.CUST_SROGT_ID AS D_CUST_SROGT_ID,
				
				CASE 
					 WHEN DC.GNDR IS NOT NULL THEN DC.GNDR
					 WHEN DC.GNDR IS NULL THEN 
								CASE WHEN RIGHT(DC.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(DC.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'M' 
								WHEN RIGHT(DC.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(DC.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'F' 
								ELSE CAST(NULL AS VARCHAR(10)) END END AS D_GNDR,			
				CASE 
					 WHEN DC.TITL IS NOT NULL THEN DC.TITL
					 WHEN DC.TITL IS NULL THEN 
								CASE WHEN RIGHT(DC.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(DC.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'MR' 
								WHEN RIGHT(DC.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(DC.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'MS'
								ELSE CAST(NULL AS VARCHAR(10)) END END AS D_TITL, 	

				TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
						FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) )  AS  D_FRST_NAME,
				
				CASE WHEN  REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0 
							THEN  TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
				              			  POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) )
							ELSE 
									CASE WHEN (DC.FRST_NAME IS NULL AND DC.MDL_NAME IS NULL AND DC.LAST_NAME IS NULL) OR (DC.FRST_NAME = '' AND DC.MDL_NAME = '' AND DC.LAST_NAME = '')
												THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
												 			FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
												ELSE 
														CASE WHEN REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(DC.FRST_NAME, '') || ' ' || COALESCE(DC.MDL_NAME, '') || ' ' || COALESCE(DC.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0
																	THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(DC.FRST_NAME, '') || ' ' || COALESCE(DC.MDL_NAME, '') || ' ' || COALESCE(DC.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
													            				POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(DC.FRST_NAME, '') || ' ' || COALESCE(DC.MDL_NAME, '') || ' ' || COALESCE(DC.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) 
														ELSE TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
																 	FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
														END
									END
				END	AS D_LAST_NAME ,
				
				TO_CHAR(DC.DT_OF_BIRTH , 'YYYY-MM-DD') ||  'T00:00:00' AS D_DT_OF_BIRTH,
				TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.FTHR_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) AS D_MOTHER_NAME,
				
				DC.IDNTFTN_TYPE_EDW_ID AS D_SSN_TYPE,
				CASE WHEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) = '' THEN CAST(NULL AS VARCHAR(10)) 
							   ELSE TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) END AS D_SSN,
				 CASE
					when DC.MBL_NUM is not null AND DC.MBL_NUM <> ''  
					THEN REGEXP_REPLACE(REGEXP_REPLACE(TRIM(DC.MBL_NUM), '[^0-9]', ''), '^(0092|[+]92|92|0)+', '')
			        when DC.PHN_RSDNC is not null AND DC.PHN_RSDNC <> '' then TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(DC.PHN_RSDNC), '[^ ]+', 1, 1), '[^0-9]', '') )
			        else 
					case 
						WHEN REGEXP_SIMILAR(DC.PHN_BUSN, '.*[A-Za-z].*') = '1' AND REGEXP_SIMILAR(DC.PHN_BUSN, '.*[0-9].*') = '1' THEN CAST(NULL AS VARCHAR(11))
						WHEN REGEXP_SIMILAR(DC.PHN_BUSN, '.*[A-Za-z].*') = '1' THEN CAST(NULL AS VARCHAR(11))
						ELSE 
							case
								when substr(regexp_replace(DC.PHN_BUSN, '[^0-9]', ''), 1,3) = '092' then substr(regexp_replace(DC.PHN_BUSN, '[^0-9]', ''), 3) 
								when substr(regexp_replace(DC.PHN_BUSN, '[^0-9]', ''), 1,2) = '92' then substr(regexp_replace(DC.PHN_BUSN, '[^0-9]', ''), 3)  
								ELSE trim(LEADING '0' FROM regexp_replace(DC.PHN_BUSN, '[^0-9]', ''))
							end
					end 
				END as D_tph_number, 	
				
				TRIM(OREPLACE(OREPLACE(
				CASE 
				WHEN TRIM(REGEXP_REPLACE(TRIM(DC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is not null AND TRIM(REGEXP_REPLACE(TRIM(DC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(DC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3
				              THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(DC.PERM_ADDR), '[^A-Za-z0-9 ]', ' ')  , '[[:space:]]+', ' '))  
				WHEN (TRIM(REGEXP_REPLACE(TRIM(DC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(DC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(DC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
						       AND (TRIM(REGEXP_REPLACE(TRIM(DC.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(DC.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(DC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
						      THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(DC.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' ')) 
				WHEN (TRIM(REGEXP_REPLACE(TRIM(DC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(DC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(DC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
						       AND ( TRIM(REGEXP_REPLACE(TRIM(DC.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(DC.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(DC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(DC.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))
				WHEN (TRIM(REGEXP_REPLACE(TRIM(DC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(DC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(DC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3 ) 
						       AND (TRIM(REGEXP_REPLACE(TRIM(DC.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(DC.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(DC.OTH_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(DC.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))		   
				ELSE CAST(NULL AS VARCHAR(10)) 
				END
				,CHR(13),' '),CHR(10), ' ')) as D_address,	

				CASE WHEN _DDO.OCPTN_DESC IS NOT NULL OR _DDO.OCPTN_DESC <> '' THEN _DDO.OCPTN_DESC ELSE 'Others' END AS D_OCCUPATION,
				
				DC.CTRY_OF_NTLTY as D_nationality1,
				'PK' as D_Residence,
				CASE WHEN DC.MBL_NUM is not null AND DC.MBL_NUM <> '' then 'PAPVT' when DC.MBL_NUM is null OR DC.MBL_NUM = '' then 'PAOFF' END as D_tph_contact_type,
				CASE WHEN DC.MBL_NUM is not null AND DC.MBL_NUM <> '' then 'COMOB' else 'COLAN' END as D_tph_communication_type,
				'92' as D_tph_country_prefix,
				
				CASE WHEN DC.PERM_ADDR is not null and DC.PERM_ADDR <> '' then 'PAPVT' 
						    when DC.PERM_ADDR is null OR DC.PERM_ADDR = '' then 'PAOFF' END as D_address_type,
							
				CASE WHEN TRIM(DC.RSDNTL_CITY) = '0' THEN CAST(NULL AS VARCHAR(10)) ELSE DC.RSDNTL_CITY END AS D_city, 
				
				'PK' as D_country_code,
				CASE  
				when substr(DC.IDNTFTN_VAL,1,1) IN ('1', '2') then 'KHYBER-PAKHTUNKHWA'
				when substr(DC.IDNTFTN_VAL,1,1) IN ('3', '6') then 'PUNJAB'
				when substr(DC.IDNTFTN_VAL,1,1) = '4' then 'SINDH'
				when substr(DC.IDNTFTN_VAL,1,1) = '5' then 'BALOCHISTAN'
				when substr(DC.IDNTFTN_VAL,1,1) = '7' then 'GILGIT-BALISTAN'
				when substr(DC.IDNTFTN_VAL,1,1) = '8' then 'AZAD-KASHMIR'
				ELSE cast(null as varchar(10)) 
				END as D_state,
				
				'ERDIR' AS D_role
				
				,ROW_NUMBER() OVER(PARTITION BY DD.CLIENT_NO_DIR ORDER BY DD.CLIENT_NO_DIR) AS RN
			FROM TRXNS T
			INNER JOIN DP_REPORTING_MART.FM_DIRECTOR_DTLS DD ON T.CUST_SROGT_ID = DD.CLIENT_NO  -- DP_SDMVW_DFDN.FM_DIRECTOR_DTLS_VW 
			LEFT JOIN DP_SDMVW_DFDN.DIM_CUST_VW DC ON DC.CUST_SROGT_ID = DD.CLIENT_NO_DIR AND DC.SYSTEM_CODE = 'CBS' 
			LEFT JOIN DP_SDMT_DFDN.DIM_OCPTN_SS _DDO ON DC.OCPTN_EDW_ID = _DDO.OCPTN_EDW_ID
			WHERE 1=1 AND DD.START_DATE = (SELECT CAST(MAX(START_DATE) AS DATE) AS START_DATE FROM DP_REPORTING_MART.FM_DIRECTOR_DTLS)
			-- CAST(CURRENT_DATE - 1 AS DATE)
		) X 
		WHERE 1=1 
		AND X.RN = 1
		)
					
		, WALKIN_DETAILS AS (
		
		SELECT * FROM (
			select 
			w.Transaction_ID,
			CASE 
			 WHEN w.Cust_Type = 'AH' AND d.GNDR IS NOT NULL THEN d.GNDR
			 WHEN w.Cust_Type = 'AH' AND d.GNDR IS NULL THEN 
						CASE WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'M' 
						WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'F' 
						ELSE CAST(NULL AS VARCHAR(10)) END 
			 WHEN w.Cust_Type = 'TP' THEN
						CASE WHEN RIGHT(W_CNIC,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(W_CNIC, '-', ''), '/', '')) = 13 THEN 'M' 
						WHEN RIGHT(W_CNIC,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(W_CNIC, '-', ''), '/', '')) = 13  THEN 'F' 
						ELSE CAST(NULL AS VARCHAR(10)) END  
			END as TFMC_Gender,

			CASE 
			 WHEN w.Cust_Type = 'AH' AND d.TITL IS NOT NULL THEN d.TITL
			 WHEN w.Cust_Type = 'AH' AND d.TITL IS NULL THEN 
						CASE WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'MR' 
						WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'MS'
						END 
			 WHEN w.Cust_Type = 'TP' THEN
						CASE WHEN RIGHT(W_CNIC,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(W_CNIC, '-', ''), '/', '')) = 13 THEN 'MR' 
						WHEN RIGHT(W_CNIC,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(W_CNIC, '-', ''), '/', '')) = 13  THEN 'MS' 
						ELSE CAST(NULL AS VARCHAR(10)) END  
			END as TFMC_Title,
			CASE 
			WHEN w.Cust_Type = 'AH'  THEN
			TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
							FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
			WHEN w.Cust_Type = 'TP'  THEN
			TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
							FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) )  
			END AS TFMC_First_Name ,

			CASE 
			WHEN w.Cust_Type = 'AH'  THEN
				CASE WHEN  REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0 
							THEN  TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
				              			  POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) )
							ELSE 
									CASE WHEN (D.FRST_NAME IS NULL AND D.MDL_NAME IS NULL AND D.LAST_NAME IS NULL) OR (D.FRST_NAME = '' AND D.MDL_NAME = '' AND D.LAST_NAME = '')
												THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
												 			FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
												ELSE 
														CASE WHEN REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0
																	THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
													            				POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) 
														ELSE TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
																 	FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
														END
									END
				END
			WHEN w.Cust_Type = 'TP'  THEN 
				CASE  		
						 WHEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
								POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) IS NULL 
								OR 
						TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
								POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) = '' 
						THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
								FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) )
						ELSE TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
								POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) END
			END AS TFMC_Last_Name ,
			CASE WHEN w.Cust_Type = 'AH'  THEN TO_CHAR(d.DT_OF_BIRTH , 'YYYY-MM-DD') ||  'T00:00:00'  WHEN w.Cust_Type = 'TP' THEN TO_CHAR(w.BIRTH_DATE  , 'YYYY-MM-DD') ||  'T00:00:00'  END as TFMC_Birth_Date,
			CASE WHEN w.Cust_Type = 'AH'  THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(d.FTHR_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) 
						 WHEN w.Cust_Type = 'TP' THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w.FATHER_NAME , '[^A-Za-z ]', ' '), ' +', ' ')) END as TFMC_Mother_Name,

			CASE WHEN w.Cust_Type = 'AH'  THEN D.IDNTFTN_TYPE_EDW_ID WHEN w.Cust_Type = 'TP' THEN 
						CASE WHEN LENGTH(REGEXP_REPLACE(w.w_cnic, '[^0-9]', '')) = 13 THEN 'NIC' 
									 WHEN REGEXP_SIMILAR( TRIM(REGEXP_REPLACE(w.w_cnic, '[^A-Za-z0-9]', '')), '^[A-Za-z0-9]+$') = 1 THEN 'PPT'  
									 ELSE CAST(NULL AS VARCHAR(10)) END
			END AS TFMC_ssn_type,
			CASE WHEN w.Cust_Type = 'AH'  THEN d.IDNTFTN_VAL WHEN w.Cust_Type = 'TP' THEN w.w_cnic END as TFMC_ssn,
			CASE WHEN w.Cust_Type = 'AH'  THEN d.CTRY_OF_NTLTY WHEN w.Cust_Type = 'TP' THEN 'PK' END as TFMC_nationality1,
			'PK' as TFMC_Residence,

			CASE WHEN w.Cust_Type = 'AH'  THEN case when d.MBL_NUM is not null AND d.MBL_NUM <> '' then 'PAPVT' when d.MBL_NUM is null OR d.MBL_NUM = '' then 'PAOFF' end
			WHEN w.Cust_Type = 'TP' THEN  'PAPVT' END as TFMC_tph_contact_type,

			CASE WHEN w.Cust_Type = 'AH'  
			THEN case when d.MBL_NUM is not null AND d.MBL_NUM <> '' then 'COMOB' else 'COLAN' end
			WHEN w.Cust_Type = 'TP' THEN  'COMOB' END as TFMC_tph_communication_type,

			'92' as TFMC_tph_country_prefix,
						
			CASE WHEN w.Cust_Type = 'AH'  THEN				  
			CASE
				when D.MBL_NUM is not null AND D.MBL_NUM <> ''  
				THEN REGEXP_REPLACE(REGEXP_REPLACE(TRIM(D.MBL_NUM), '[^0-9]', ''), '^(0092|[+]92|92|0)+', '')
		        when D.PHN_RSDNC is not null AND D.PHN_RSDNC <> '' then TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.PHN_RSDNC), '[^ ]+', 1, 1), '[^0-9]', '') )
		        else 
				case 
					WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' AND REGEXP_SIMILAR(D.PHN_BUSN, '.*[0-9].*') = '1' THEN CAST(NULL AS VARCHAR(11))
					WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' THEN CAST(NULL AS VARCHAR(11))
					ELSE 
						case
							when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,3) = '092' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3) 
							when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,2) = '92' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3)  
							ELSE trim(LEADING '0' FROM regexp_replace(D.PHN_BUSN, '[^0-9]', ''))
						end
				end 
			END		    
			WHEN w.Cust_Type = 'TP' THEN  TRIM(LEADING '0' FROM w.CONTACT_NO) END as TFMC_tph_number,

			CASE WHEN w.Cust_Type = 'AH'  THEN	
			CASE WHEN D.PERM_ADDR is not null and D.PERM_ADDR <> '' then 'PAPVT' 
						when D.PERM_ADDR is null OR D.PERM_ADDR = '' then 'PAOFF' END
			WHEN w.Cust_Type = 'TP' THEN  'PAPVT' END as TFMC_address_type,

			TRIM(OREPLACE(OREPLACE( 	
			CASE WHEN w.Cust_Type = 'AH'  THEN	
					CASE 
					WHEN TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is not null AND TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3
					              THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' ')  , '[[:space:]]+', ' '))  
					WHEN (TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
							       AND (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							      THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' ')) 
					WHEN (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
							       AND ( TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
								   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))
					WHEN (TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3 ) 
							       AND (TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
								   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))		   
					ELSE CAST(NULL AS VARCHAR(10)) 
					END
			WHEN w.Cust_Type = 'TP' THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(w.CUSTOMER_ADDRESS), '[^A-Za-z0-9 ]', ' ')  , '[[:space:]]+', ' ')) END ,CHR(13),' '),CHR(10), ' ')) as TFMC_address,

			--CASE WHEN w.Cust_Type = 'AH'  THEN	CASE WHEN REGEXP_REPLACE(TRIM(d.RSDNTL_CITY), '[^A-Za-z ]', '') = '' THEN CAST(NULL AS VARCHAR(10)) ELSE REGEXP_REPLACE(TRIM(d.RSDNTL_CITY), '[^A-Za-z ]', '') END
			--WHEN w.Cust_Type = 'TP' THEN CAST(NULL	AS VARCHAR(10)) END as TFMC_city,

			B.CITY_NAME AS TFMC_city, 
			
			'PK' as TFMC_country_code,
			CASE WHEN w.Cust_Type = 'AH'  THEN
			case 
			when substr(d.IDNTFTN_VAL,1,1) IN ('1', '2') then 'KHYBER-PAKHTUNKHWA'
			when substr(d.IDNTFTN_VAL,1,1) IN ('3', '6') then 'PUNJAB'
			when substr(d.IDNTFTN_VAL,1,1) = '4' then 'SINDH'
			when substr(d.IDNTFTN_VAL,1,1) = '5' then 'BALOCHISTAN'
			when substr(d.IDNTFTN_VAL,1,1) = '7' then 'GILGIT-BALISTAN'
			when substr(d.IDNTFTN_VAL,1,1) = '8' then 'AZAD-KASHMIR'
			ELSE cast(null as varchar(10)) 
			end
			WHEN w.Cust_Type = 'TP' THEN  
			case 
			when substr(W.W_CNIC,1,1) IN ('1', '2') then 'KHYBER-PAKHTUNKHWA'
			when substr(W.W_CNIC,1,1) IN ('3', '6') then 'PUNJAB'
			when substr(W.W_CNIC,1,1) = '4' then 'SINDH'
			when substr(W.W_CNIC,1,1) = '5' then 'BALOCHISTAN'
			when substr(W.W_CNIC,1,1) = '7' then 'GILGIT-BALISTAN'
			when substr(W.W_CNIC,1,1) = '8' then 'AZAD-KASHMIR'
			ELSE cast(null as varchar(10)) 
			end
			END as TFMC_state,

			CASE WHEN w.Cust_Type = 'AH'  THEN CASE WHEN O.OCPTN_DESC IS NOT NULL OR O.OCPTN_DESC <> '' THEN O.OCPTN_DESC ELSE 'Others' END
			WHEN w.Cust_Type = 'TP' THEN W.w_source_of_funds END AS TFMC_occupation,
			'PK' as TFMC_from_country,
			
			DENSE_RANK() OVER(PARTITION BY d.IDNTFTN_VAL ORDER BY d.START_DATE DESC) AS RN
			
			FROM TRXNS T
			INNER JOIN dp_sdmt_dfdn.WALKIN_TXN W on T.tsactn_id = w.Transaction_ID 
			LEFT JOIN DP_SDMVW_DFDN.DIM_CUST_VW d ON d.IDNTFTN_VAL = w.w_cnic and d.system_code = 'CBS'
			LEFT JOIN DP_SDMT_DFDN.DIM_OCPTN_SS O ON O.OCPTN_EDW_ID = D.OCPTN_EDW_ID  and d.system_code = 'CBS'
			LEFT JOIN DP_SDMVW_DFDN.DIM_BRNCH_HIERARCHY_VW B ON T.BRNCH_SROGT_ID = B.BRNCH_SROGT_ID
			WHERE 1=1
			) X
		WHERE 1=1 
		AND X.RN = 1
		AND X.TFMC_ssn_type NOT IN ('BFN', 'FXP')
		)
		
		, Final_Chunk AS (
		SELECT 
		T.CATEGORY,
		T.CATEGORY_TYPE_DESC,
		TRIM(T.TSACTN_ID) AS transactionnumber,
		B.BRNCH_DESC || ' (' || T.BRNCH_SROGT_ID || ')' AS transaction_location,
		CASE 
		WHEN CR_DR_IND = 'D' THEN 'CHEQUE WITHDRAWAL'  
		WHEN CR_DR_IND = 'C' THEN 'CASH DEPOSIT' 
		END AS transaction_description,
		TO_CHAR(T.TSACTN_DT , 'YYYY-MM-DD') ||  'T00:00:00' as date_transaction,
		B.BRNCH_DESC || ' (' || T.BRNCH_SROGT_ID || ')' AS teller,
		B.CITY_NAME AS authorized,
		'TMBRN' AS transmode_code,
		CASE WHEN T.CURY_EDW_ID = 'PKR' THEN CAST(T.TSACTN_AMT AS INT)
		ELSE CAST(T.FRGN_TSACTN_AMT_PKR AS INT) END AS amount_local,   
		CASE 
		WHEN CR_DR_IND = 'D' THEN 'FTCHQ'  
		WHEN CR_DR_IND = 'C' THEN 'FTCAS'
		END AS TFMC_from_funds_code,
		W.TFMC_Gender,
		W.TFMC_Title,
		W.TFMC_First_Name,
		W.TFMC_Last_Name,
		W.TFMC_Birth_Date,
		W.TFMC_Mother_Name,
		W.TFMC_ssn_type,
		W.TFMC_ssn,
		W.TFMC_nationality1,
		W.TFMC_Residence,
		W.TFMC_tph_contact_type,
		W.TFMC_tph_communication_type,
		W.TFMC_tph_country_prefix,
		W.TFMC_tph_number,
		W.TFMC_address_type,
		W.TFMC_address,
		W.TFMC_city,
		W.TFMC_country_code,
		W.TFMC_state,
		W.TFMC_occupation,
		W.TFMC_from_country,
		CASE 
		WHEN CR_DR_IND = 'D' THEN 'FTCAS'
		WHEN CR_DR_IND = 'C' THEN 'FTDEP' 
		END AS TTMC_to_funds_code,
		'UBL Bank Limited' AS TTMC_institution_name,
		'43' AS TTMC_institution_code,
		'FALSE' AS TTMC_non_bank_institution,
		BB.BRNCH_DESC || ' (' || T.ACCT_BRNCH_SROGT_ID || ')'  AS TTMC_branch,
		T.ACCT_SROGT_ID AS TTMC_account,
		T.ACCT_CURY_EDW_ID AS TTMC_currency_code,
		T.FRGN_CCY AS TTMC_Foreign_Currency_Code,
		T.FRGN_TSACTN_AMT AS TTMC_Foreign_Amount,
		T.EXCHANGE_RATE AS TTMC_Foreign_Exchange_Rate,
		T.ACCT_DESC AS TTMC_account_name,
		T.ACCT_TYPE_DESC AS TTMC_Acct_Type_Desc,
		T.ACCT_TYPE_CODE AS TTMC_personal_account_type,
		T.ACCT_DESC AS TTMC_name,
		T.CATEGORY_TYPE_CODE AS TTMC_incorporation_legal_form,
		T.CATEGORY_TYPE_DESC AS TTMC_Category_Type_Desc,
		OREPLACE(BUS.BUSINESS_DESC, '"', '') AS TTMC_business,

		case when d.MBL_NUM is not null and d.MBL_NUM <> '' then 'PAPVT' 
				  when d.MBL_NUM is null OR d.MBL_NUM = '' then 'PAOFF' end as TTMC_tph_contact_type,
		case when d.MBL_NUM is not null and d.MBL_NUM <> '' then 'COMOB' else 'COLAN' end as TTMC_tph_communication_type,
		'92' as TTMC_tph_country_prefix,			  
        CASE
			when D.MBL_NUM is not null AND D.MBL_NUM <> ''  
			THEN REGEXP_REPLACE(REGEXP_REPLACE(TRIM(D.MBL_NUM), '[^0-9]', ''), '^(0092|[+]92|92|0)+', '')
	        when D.PHN_RSDNC is not null AND D.PHN_RSDNC <> '' then TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.PHN_RSDNC), '[^ ]+', 1, 1), '[^0-9]', '') )
	        else 
			case 
				WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' AND REGEXP_SIMILAR(D.PHN_BUSN, '.*[0-9].*') = '1' THEN CAST(NULL AS VARCHAR(11))
				WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' THEN CAST(NULL AS VARCHAR(11))
				ELSE 
					case
						when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,3) = '092' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3) 
						when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,2) = '92' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3)  
						ELSE trim(LEADING '0' FROM regexp_replace(D.PHN_BUSN, '[^0-9]', ''))
					end
			end 
		END as TTMC_tph_number, 				  

		case when d.PERM_ADDR is not null and d.PERM_ADDR <> '' then 'PAPVT' 
					when d.PERM_ADDR is null OR d.PERM_ADDR = '' then 'PAOFF' end as TTMC_address_type,

	   TRIM(OREPLACE(OREPLACE( 
		CASE 
		WHEN TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is not null AND TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3
		              THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' ')  , '[[:space:]]+', ' '))  
		WHEN (TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
				       AND (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
				      THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' ')) 
		WHEN (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
				       AND ( TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
					   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))
		WHEN (TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3 ) 
				       AND (TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
					   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))		   
		ELSE CAST(NULL AS VARCHAR(10)) 
		END
		,CHR(13),' '),CHR(10), ' ')) as TTMC_address,
		BB.CITY_NAME AS TTMC_city,
		'PK' as TTMC_country_code,
		CASE WHEN BB.PROV_NAME = 'FATA' THEN 'KHYBER-PAKHTUNKHWA'
					WHEN BB.PROV_NAME = 'ISLAMABAD' THEN 'PUNJAB'
					ELSE BB.PROV_NAME 
		END AS TTMC_State,
		'PK' AS TTMC_incorporation_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN 
					CASE 
					 WHEN d.GNDR IS NOT NULL THEN d.GNDR
					 WHEN d.GNDR IS NULL THEN 
								CASE WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'M' 
								WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'F' 
								ELSE CAST(NULL AS VARCHAR(10)) END END
			END
		) AS DIR1_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN 
					CASE 
					 WHEN d.TITL IS NOT NULL THEN d.TITL
					 WHEN d.TITL IS NULL THEN 
								CASE WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'MR' 
								WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'MS'
								ELSE CAST(NULL AS VARCHAR(10)) END END
			END
		) AS DIR1_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z0-9 ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
						FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
			END
		) AS DIR1_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN 
				CASE WHEN  REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0 
							THEN  TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
				              			  POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) )
							ELSE 
									CASE WHEN (D.FRST_NAME IS NULL AND D.MDL_NAME IS NULL AND D.LAST_NAME IS NULL) OR (D.FRST_NAME = '' AND D.MDL_NAME = '' AND D.LAST_NAME = '')
												THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
												 			FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
												ELSE 
														CASE WHEN REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0
																	THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
													            				POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) 
														ELSE TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
																 	FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
														END
									END
				END
			END
		) AS DIR1_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN TO_CHAR(D.DT_OF_BIRTH , 'YYYY-MM-DD') ||  'T00:00:00' 
			END
		) AS DIR1_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.FTHR_NAME, '[^A-Za-z ]', ' '), ' +', ' '))
			END
		) AS DIR1_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN D.IDNTFTN_TYPE_EDW_ID 
			END
		) AS DIR1_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN
							CASE WHEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) = '' THEN CAST(NULL AS VARCHAR(10)) 
											   ELSE TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) END
			END
		) AS DIR1_SSN

		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN D.CTRY_OF_NTLTY
			END
		) AS DIR1_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN 'PK'
			END
		) AS DIR1_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN
						  CASE WHEN D.MBL_NUM is not null AND D.MBL_NUM <> '' then 'PAPVT' when D.MBL_NUM is null OR D.MBL_NUM = '' then 'PAOFF' END
			END
		) AS DIR1_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN
						  CASE WHEN D.MBL_NUM is not null AND D.MBL_NUM <> '' then 'COMOB' else 'COLAN' END
			END
		) AS DIR1_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN '92'
			END
		) AS DIR1_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN 		
			
			CASE when D.MBL_NUM is not null AND D.MBL_NUM <> ''  
			THEN REGEXP_REPLACE(REGEXP_REPLACE(TRIM(D.MBL_NUM), '[^0-9]', ''), '^(0092|[+]92|92|0)+', '')
	        when D.PHN_RSDNC is not null AND D.PHN_RSDNC <> '' then TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.PHN_RSDNC), '[^ ]+', 1, 1), '[^0-9]', '') )
	        else case WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' AND REGEXP_SIMILAR(D.PHN_BUSN, '.*[0-9].*') = '1' THEN CAST(NULL AS VARCHAR(11)) WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' THEN CAST(NULL AS VARCHAR(11))
			ELSE case when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,3) = '092' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3) when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,2) = '92' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3)  
			ELSE trim(LEADING '0' FROM regexp_replace(D.PHN_BUSN, '[^0-9]', '')) end end END	
			END
		) AS DIR1_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN
						 CASE WHEN D.PERM_ADDR is not null and D.PERM_ADDR <> '' then 'PAPVT' 
									 WHEN D.PERM_ADDR is null OR D.PERM_ADDR = '' then 'PAOFF' END
			END
		) AS DIR1_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN 
				CASE 
				WHEN TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is not null AND TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3
				              THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' ')  , '[[:space:]]+', ' '))  
				WHEN (TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
						       AND (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
						      THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' ')) 
				WHEN (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
						       AND ( TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))
				WHEN (TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3 ) 
						       AND (TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))		   
				ELSE CAST(NULL AS VARCHAR(10)) 
				END
			END
		) AS DIR1_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CASE WHEN TRIM(D.RSDNTL_CITY)  = '0' THEN CAST(NULL AS VARCHAR(10)) ELSE D.RSDNTL_CITY END 
			END
		) AS DIR1_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN 'PK'
			END
		) AS DIR1_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN 
						 CASE  
							when substr(D.IDNTFTN_VAL,1,1) IN ('1', '2') then 'KHYBER-PAKHTUNKHWA'
							when substr(D.IDNTFTN_VAL,1,1) IN ('3', '6') then 'PUNJAB'
							when substr(D.IDNTFTN_VAL,1,1) = '4' then 'SINDH'
							when substr(D.IDNTFTN_VAL,1,1) = '5' then 'BALOCHISTAN'
							when substr(D.IDNTFTN_VAL,1,1) = '7' then 'GILGIT-BALISTAN'
							when substr(D.IDNTFTN_VAL,1,1) = '8' then 'AZAD-KASHMIR'
							ELSE cast(null as varchar(10)) 
						END 
			END
		) AS DIR1_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN  CASE WHEN _DO.OCPTN_DESC IS NOT NULL OR _DO.OCPTN_DESC <> '' THEN _DO.OCPTN_DESC ELSE 'Others' END 
			END
		) AS DIR1_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR1_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_FATHER_NAME

        , MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR2_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS DIR3_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR3_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR4_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR5_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_SSN

		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR6_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR7_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR8_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 9  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR9_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS DIR10_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 10  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR10_ROLE
	
		, CASE WHEN TRIM(LEADING '0' FROM REGEXP_REPLACE(D.TAX_NUM, '[^0-9]', '')) = '' THEN NULL 
		ELSE TRIM(LEADING '0' FROM REGEXP_REPLACE(D.TAX_NUM, '[^0-9]', '')) END AS TMC_TAX_NUM
		
		
		, MAX('TRUE') AS SIGNATORY1_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 1  THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 1 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND  DD.D_RN IS NULL THEN 
						CASE 
							 WHEN d.GNDR IS NOT NULL THEN d.GNDR
							 WHEN d.GNDR IS NULL THEN 
										CASE WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'M' 
										WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'F' 
										ELSE CAST(NULL AS VARCHAR(10)) END END
			END
		) AS SIGNATORY1_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN 
					CASE 
					 WHEN d.TITL IS NOT NULL THEN d.TITL
					 WHEN d.TITL IS NULL THEN 
								CASE WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'MR' 
								WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'MS'
								ELSE CAST(NULL AS VARCHAR(10)) END END
			END
		) AS SIGNATORY1_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 1  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN  TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
						FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
			END
		) AS SIGNATORY1_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 1  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN 
					CASE WHEN  REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0 
								THEN  TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
					              			  POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) )
								ELSE 
										CASE WHEN (D.FRST_NAME IS NULL AND D.MDL_NAME IS NULL AND D.LAST_NAME IS NULL) OR (D.FRST_NAME = '' AND D.MDL_NAME = '' AND D.LAST_NAME = '')
													THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
													 			FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
													ELSE 
															CASE WHEN REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0
																		THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
														            				POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) 
															ELSE TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
																	 	FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
															END
										END
					END
			END
		) AS SIGNATORY1_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.FTHR_NAME, '[^A-Za-z ]', ' '), ' +', ' '))
			END
		) AS SIGNATORY1_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN D.IDNTFTN_TYPE_EDW_ID 
			END
		) AS SIGNATORY1_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN 
							CASE WHEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) = '' THEN CAST(NULL AS VARCHAR(10)) 
															   ELSE TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) END
			END
		) AS SIGNATORY1_SSN
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN D.CTRY_OF_NTLTY
			END
		) AS SIGNATORY1_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN 'PK'
			END
		) AS SIGNATORY1_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN 
						  CASE WHEN D.MBL_NUM is not null AND D.MBL_NUM <> '' then 'PAPVT' when D.MBL_NUM is null OR D.MBL_NUM = '' then 'PAOFF' END
			END
		) AS SIGNATORY1_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN 
						  CASE WHEN D.MBL_NUM is not null AND D.MBL_NUM <> '' then 'COMOB' else 'COLAN' END
			END
		) AS SIGNATORY1_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN '92'
			END
		) AS SIGNATORY1_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN 
			CASE when D.MBL_NUM is not null AND D.MBL_NUM <> ''  
			THEN REGEXP_REPLACE(REGEXP_REPLACE(TRIM(D.MBL_NUM), '[^0-9]', ''), '^(0092|[+]92|92|0)+', '')
	        when D.PHN_RSDNC is not null AND D.PHN_RSDNC <> '' then TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.PHN_RSDNC), '[^ ]+', 1, 1), '[^0-9]', '') )
	        else case WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' AND REGEXP_SIMILAR(D.PHN_BUSN, '.*[0-9].*') = '1' THEN CAST(NULL AS VARCHAR(11)) WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' THEN CAST(NULL AS VARCHAR(11))
			ELSE case when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,3) = '092' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3) when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,2) = '92' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3)  
			ELSE trim(LEADING '0' FROM regexp_replace(D.PHN_BUSN, '[^0-9]', '')) end end END	
			END
		) AS SIGNATORY1_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN TO_CHAR(D.DT_OF_BIRTH , 'YYYY-MM-DD') ||  'T00:00:00'
			END
		) AS SIGNATORY1_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CASE WHEN D.PERM_ADDR is not null and D.PERM_ADDR <> '' then 'PAPVT'  WHEN D.PERM_ADDR is null OR D.PERM_ADDR = '' then 'PAOFF' END
			END
		) AS SIGNATORY1_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN
			CASE 
				WHEN TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is not null AND TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3
				              THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' ')  , '[[:space:]]+', ' '))  
				WHEN (TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
						       AND (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
						      THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' ')) 
				WHEN (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
						       AND ( TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))
				WHEN (TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3 ) 
						       AND (TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))		   
				ELSE CAST(NULL AS VARCHAR(10)) 
				END
			END
		) AS SIGNATORY1_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CASE WHEN TRIM(D.RSDNTL_CITY)  = '0' THEN CAST(NULL AS VARCHAR(10)) ELSE D.RSDNTL_CITY END
			END
		) AS SIGNATORY1_CITY
	
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN 'PK'
			END
		) AS SIGNATORY1_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN 
						  CASE  
							when substr(D.IDNTFTN_VAL,1,1) IN ('1', '2') then 'KHYBER-PAKHTUNKHWA'
							when substr(D.IDNTFTN_VAL,1,1) IN ('3', '6') then 'PUNJAB'
							when substr(D.IDNTFTN_VAL,1,1) = '4' then 'SINDH'
							when substr(D.IDNTFTN_VAL,1,1) = '5' then 'BALOCHISTAN'
							when substr(D.IDNTFTN_VAL,1,1) = '7' then 'GILGIT-BALISTAN'
							when substr(D.IDNTFTN_VAL,1,1) = '8' then 'AZAD-KASHMIR'
							ELSE cast(null as varchar(10)) 
						END
			END
		) AS SIGNATORY1_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CASE WHEN _DO.OCPTN_DESC IS NOT NULL OR _DO.OCPTN_DESC <> '' THEN _DO.OCPTN_DESC ELSE 'Others' END 
			END
		) AS SIGNATORY1_OCCUPATION
		
		, MAX(
			'ARPYS' 
		) AS SIGNATORY1_ROLE
		
		-----------------------------------------------------------------------------------------------------------------------------------------------------------
		, MAX('TRUE') AS SIGNATORY2_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 2 THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 2 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2 THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 2  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY2_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 2  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY2_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY2_SSN
		
		 , MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_CITY
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 2 THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_OCCUPATION
		
		, MAX(
			'ARPYS'
		) AS SIGNATORY2_ROLE
		 
		, MAX('TRUE') AS SIGNATORY3_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 3 THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 3 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3 THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 3  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY3_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 3  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY3_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY3_SSN
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_CITY
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 3 THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_OCCUPATION
		
		, MAX(
			'ARPYS'
		) AS SIGNATORY3_ROLE
		
		, MAX('TRUE') AS SIGNATORY4_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 4 THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 4 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4 THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 4  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY4_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 4  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY4_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY4_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY4_SSN
		
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_CITY
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 4 THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_OCCUPATION
		
		, MAX(
			'ARPYS'
		) AS SIGNATORY4_ROLE
		
		, MAX('TRUE') AS SIGNATORY5_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 5 THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 5 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5 THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 5  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY5_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 5  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY5_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY5_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY5_SSN
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_CITY
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 5 THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_OCCUPATION
		
		, MAX(
			'ARPYS'
		) AS SIGNATORY5_ROLE
		
		, MAX('TRUE') AS SIGNATORY6_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 6 THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 6 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6 THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 6  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY6_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 6  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY6_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY6_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY6_SSN
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_CITY
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 6 THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_OCCUPATION
		
		, MAX(
			'ARPYS'
		) AS SIGNATORY6_ROLE
		
		, MAX('TRUE') AS SIGNATORY7_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 7 THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 7 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7 THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 7  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY7_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 7  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY7_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY7_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY7_SSN
		
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_CITY
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 7 THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_OCCUPATION
		
		, MAX(
			'ARPYS'
		) AS SIGNATORY7_ROLE
		
		, MAX('TRUE') AS SIGNATORY8_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 8 THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 8 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8 THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 8  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY8_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 8  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY8_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY8_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY8_SSN
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_CITY
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 8 THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_OCCUPATION
		
		, MAX(
			'ARPYS'
		) AS SIGNATORY8_ROLE
		
		, TO_CHAR(T.ACCT_ORIGNL_OPN_DT , 'YYYY-MM-DD') ||  'T00:00:00' AS TTMC_open,
		'ASACT' as TTMC_status_code,
		'PK' AS TTMC_to_country

		FROM TRXNS T
		LEFT JOIN DP_SDMVW_DFDN.DIM_CUST_VW d ON d.CUST_SROGT_ID = T.CUST_SROGT_ID and d.system_code = 'CBS'
		LEFT JOIN DP_SDMT_DFDN.DIM_OCPTN_SS _DO ON D.OCPTN_EDW_ID = _DO.OCPTN_EDW_ID
		LEFT JOIN DP_WRK_CBS.FM_CLIENT_DAILY fmd ON fmd.client_no = T.CUST_SROGT_ID
		LEFT JOIN DP_SDMVW_DFDN.DIM_BUSINESS_VW BUS ON fmd.business = bus.BUSINESS
		LEFT JOIN DP_SDMVW_DFDN.DIM_CUST_TYPE_VW CTY ON D.CUST_TYPE_EDW_ID = CTY.CUST_TYPE_EDW_ID
		LEFT JOIN DP_SDMVW_DFDN.DIM_BRNCH_HIERARCHY_VW B ON T.BRNCH_SROGT_ID = B.BRNCH_SROGT_ID
		LEFT JOIN DP_SDMVW_DFDN.DIM_BRNCH_HIERARCHY_VW BB ON T.ACCT_BRNCH_SROGT_ID = BB.BRNCH_SROGT_ID 
		LEFT JOIN MANDATE M ON M.ACCT_SROGT_ID = T.ACCT_SROGT_ID
		LEFT JOIN DIRECTORS DD ON DD.CUST_SROGT_ID = T.CUST_SROGT_ID 
		LEFT JOIN WALKIN_DETAILS W ON W.Transaction_ID = T.TSACTN_ID
		WHERE 1=1 
		GROUP BY 
		t.CATEGORY, CATEGORY_TYPE_DESC,transactionnumber,transaction_location,transaction_description,date_transaction,teller,authorized,transmode_code,amount_local,TFMC_from_funds_code,TFMC_Gender,
		TFMC_Title,TFMC_First_Name,TFMC_Last_Name,TFMC_Birth_Date,TFMC_Mother_Name,TFMC_ssn_type,TFMC_ssn,TFMC_nationality1,TFMC_Residence,TFMC_tph_contact_type,
		TFMC_tph_communication_type,TFMC_tph_country_prefix,TFMC_tph_number,TFMC_address_type,TFMC_address,TFMC_city,TFMC_country_code,TFMC_state,TFMC_occupation,
		TFMC_from_country,TTMC_to_funds_code,TTMC_institution_name,TTMC_institution_code,TTMC_non_bank_institution,TTMC_branch,TTMC_account,TTMC_currency_code,
		TTMC_Foreign_Currency_Code, TTMC_Foreign_Amount, TTMC_Foreign_Exchange_Rate, TTMC_account_name,TTMC_Acct_Type_Desc,TTMC_personal_account_type,TTMC_name,TTMC_incorporation_legal_form, TTMC_Category_Type_Desc,
		TTMC_business,TTMC_tph_contact_type,TTMC_tph_communication_type, TTMC_tph_country_prefix,TTMC_tph_number,TTMC_address_type,TTMC_address,TTMC_city,TTMC_country_code,
		TTMC_state,TTMC_incorporation_country_code,TMC_TAX_NUM, TTMC_open,TTMC_status_code,TTMC_to_country 
		)

		, DATA_V1 AS ( 
		
		SELECT 
		CAST(CATEGORY AS VARCHAR(10)) AS CATEGORY, 
	    CAST(CATEGORY_TYPE_DESC AS VARCHAR(99)) AS SYS_CATEGORY,
		CAST(transactionnumber AS BIGINT) AS transactionnumber,
		CAST(transaction_location AS VARCHAR(99)) AS transaction_location,
		CAST(transaction_description AS VARCHAR(99)) AS transaction_description,
		CAST(date_transaction AS VARCHAR(20)) AS date_transaction,
		CAST(teller AS VARCHAR(99)) AS teller ,
		CAST(authorized AS VARCHAR(99)) AS authorized,
		CAST(transmode_code AS VARCHAR(10)) AS transmode_code,
		CAST(amount_local AS INT) AS amount_local,
	    CAST(TFMC_from_funds_code AS VARCHAR(10)) AS TFMC_from_funds_code,
		CAST(TFMC_Gender AS VARCHAR(10)) AS TFMC_Gender,
		CAST(TFMC_Title AS VARCHAR(99)) AS TFMC_Title,
		CAST(TFMC_First_Name AS VARCHAR(99)) AS TFMC_First_Name,
		CAST(TFMC_Last_Name AS VARCHAR(99)) AS TFMC_Last_Name,
		CASE WHEN TFMC_Birth_Date LIKE '00%'  THEN '19' || SUBSTR(TFMC_Birth_Date, 3) ELSE TFMC_Birth_Date END AS TFMC_Birth_Date,
		--CAST(TFMC_Birth_Date AS VARCHAR(20)) AS TFMC_Birth_Date,
		CAST(TFMC_Mother_Name AS VARCHAR(99)) AS TFMC_Mother_Name,
		CAST(TFMC_ssn_type AS VARCHAR(10)) AS TFMC_ssn_type,
		CAST(CASE WHEN TFMC_ssn_type IN ('NIC', 'PPT','POC') THEN TFMC_ssn ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS TFMC_ssn,
		CAST(CASE WHEN TFMC_ssn_type= 'NIC' THEN 'PK' ELSE TFMC_nationality1 END  AS VARCHAR(20)) AS TFMC_nationality1, 
		CAST(TFMC_Residence AS VARCHAR(20)) AS TFMC_Residence,
		CAST(TFMC_tph_contact_type AS VARCHAR(20)) AS TFMC_tph_contact_type,
		CAST(TFMC_tph_communication_type AS VARCHAR(20)) AS TFMC_tph_communication_type,
		CAST(TFMC_tph_country_prefix AS VARCHAR(10)) AS TFMC_tph_country_prefix,
		CAST(TFMC_tph_number AS VARCHAR(20)) AS TFMC_tph_number,
		CAST(TFMC_address_type AS VARCHAR(10)) AS TFMC_address_type,
		CAST(TFMC_address AS VARCHAR(99)) AS TFMC_address,
		CAST(TFMC_city AS VARCHAR(50)) AS TFMC_city,
		CAST(TFMC_country_code AS VARCHAR(10)) AS TFMC_country_code,
		CAST(TFMC_state AS VARCHAR(50)) AS TFMC_state,
		CAST(TFMC_occupation AS VARCHAR(99)) AS TFMC_occupation,
		CAST(TFMC_from_country AS VARCHAR(20)) AS TFMC_from_country,
		CAST(TTMC_to_funds_code AS VARCHAR(20)) AS TTMC_to_funds_code,
		CAST(TTMC_institution_name AS VARCHAR(99)) AS TTMC_institution_name,
		CAST(TTMC_institution_code AS VARCHAR(99)) AS TTMC_institution_code,
		CAST(TTMC_non_bank_institution AS VARCHAR(99)) AS TTMC_non_bank_institution,
		CAST(TTMC_branch AS VARCHAR(99)) AS TTMC_branch,
		CAST(TTMC_account AS VARCHAR(20)) AS TTMC_account,
		CAST(TTMC_currency_code AS VARCHAR(10)) AS TTMC_currency_code,
		CAST(TTMC_Foreign_Currency_Code AS VARCHAR(10)) AS TTMC_Foreign_Currency_Code,
		CAST(TTMC_Foreign_Amount AS INT) AS TTMC_Foreign_Amount  ,
		CAST(TTMC_Foreign_Exchange_Rate AS DECIMAL(38,4)) AS TTMC_Foreign_Exchange_Rate,
		CAST(TTMC_account_name AS VARCHAR(99)) AS TTMC_account_name, 
		CAST(TTMC_personal_account_type AS VARCHAR(20)) AS TTMC_personal_account_type, 
		CAST(TTMC_name AS VARCHAR(99)) AS TTMC_name, 
		CAST(TTMC_incorporation_legal_form AS VARCHAR(20)) AS TTMC_incorporation_legal_form, 
		CAST(TTMC_business AS VARCHAR(99)) AS TTMC_business, 
		CAST(TTMC_tph_contact_type AS VARCHAR(20)) AS TTMC_tph_contact_type, 
		CAST(TTMC_tph_communication_type AS VARCHAR(20)) AS TTMC_tph_communication_type, 
		CAST(TTMC_tph_country_prefix AS VARCHAR(10)) AS TTMC_tph_country_prefix ,
		CAST(CASE WHEN TTMC_tph_number IS NULL OR TTMC_tph_number = '' THEN COALESCE(SIGNATORY1_TPH_NUMBER, DIR1_TPH_NUMBER) ELSE TTMC_tph_number END AS VARCHAR(20)) AS TTMC_tph_number,
		CAST(TTMC_address_type AS VARCHAR(10)) AS TTMC_address_type,
		CAST(CASE WHEN TTMC_address IS NULL OR TTMC_address = '' THEN COALESCE(SIGNATORY1_ADDRESS, DIR1_ADDRESS) ELSE TTMC_address END AS VARCHAR(99)) AS TTMC_address,
		CAST(TTMC_city AS VARCHAR(50)) AS TTMC_city,
		CAST(TTMC_country_code AS VARCHAR(10)) AS TTMC_country_code,
		CAST(TTMC_state AS VARCHAR(50)) AS TTMC_state,
		CAST(TTMC_incorporation_country_code AS VARCHAR(20)) AS TTMC_incorporation_country_code,
		------------------------------------- DIRECTOR 1 -----------------------------------------
		CAST(DIR1_GNDR AS VARCHAR(10)) AS DIR1_GNDR,
		CAST(DIR1_TITL AS VARCHAR(10)) AS DIR1_TITL,
		CAST(DIR1_FIRSTNAME AS VARCHAR(99)) AS DIR1_FIRSTNAME,
		CAST(DIR1_LASTNAME AS VARCHAR(99)) AS DIR1_LASTNAME,
		CAST(DIR1_FATHER_NAME AS VARCHAR(99)) AS DIR1_FATHER_NAME,
		CAST(DIR1_SSN_TYPE AS VARCHAR(10)) AS DIR1_SSN_TYPE,
		CAST(CASE WHEN DIR1_SSN_TYPE IN ('NIC', 'PPT','POC') THEN DIR1_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR1_SSN,
	    CAST(DIR1_nationality1 AS VARCHAR(10)) AS DIR1_nationality1,
	    CAST(DIR1_Residence AS VARCHAR(10)) AS DIR1_Residence,
	    CAST(DIR1_tph_contact_type AS VARCHAR(10)) AS DIR1_tph_contact_type,
	    CAST(DIR1_tph_communication_type AS VARCHAR(10)) AS DIR1_tph_communication_type,
	    CAST(DIR1_tph_country_prefix AS VARCHAR(10)) AS DIR1_tph_country_prefix,
		CAST(CASE WHEN DIR1_TPH_NUMBER IS NULL OR DIR1_TPH_NUMBER = '' THEN 
					COALESCE(CASE WHEN SIGNATORY1_TPH_NUMBER IS NULL OR SIGNATORY1_TPH_NUMBER = '' THEN TTMC_tph_number END, SIGNATORY1_TPH_NUMBER ) ELSE DIR1_TPH_NUMBER END AS VARCHAR(50)) AS DIR1_TPH_NUMBER,
		CAST(CASE WHEN DIR1_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR1_DATE_OF_BIRTH, 3) ELSE DIR1_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR1_DATE_OF_BIRTH,
	    CAST(DIR1_address_type AS VARCHAR(10)) AS DIR1_address_type,
		CAST(DIR1_ADDRESS AS VARCHAR(99)) AS DIR1_ADDRESS,
	    CAST(DIR1_CITY AS VARCHAR(20)) AS DIR1_CITY,
	    CAST(DIR1_country_code AS VARCHAR(10)) AS DIR1_country_code,
	    CAST(DIR1_STATE AS VARCHAR(20)) AS DIR1_STATE,
		CAST(DIR1_OCCUPATION AS VARCHAR(99)) AS DIR1_OCCUPATION,
	    CAST(DIR1_ROLE AS VARCHAR(10)) AS DIR1_ROLE,
		------------------------------------- DIRECTOR 2 -----------------------------------------
		CAST(DIR2_GNDR AS VARCHAR(10)) AS DIR2_GNDR,
		CAST(DIR2_TITL AS VARCHAR(10)) AS DIR2_TITL,
		CAST(DIR2_FIRSTNAME AS VARCHAR(99)) AS DIR2_FIRSTNAME,
		CAST(DIR2_LASTNAME AS VARCHAR(99)) AS DIR2_LASTNAME,
		CAST(DIR2_FATHER_NAME AS VARCHAR(99)) AS DIR2_FATHER_NAME,
		CAST(DIR2_SSN_TYPE AS VARCHAR(10)) AS DIR2_SSN_TYPE,
		CAST(CASE WHEN DIR2_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR2_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR2_SSN,
	    CAST(DIR2_nationality1 AS VARCHAR(10)) AS DIR2_nationality1,
	    CAST(DIR2_Residence AS VARCHAR(10)) AS DIR2_Residence,
	    CAST(DIR2_tph_contact_type AS VARCHAR(10)) AS DIR2_tph_contact_type,
	    CAST(DIR2_tph_communication_type AS VARCHAR(10)) AS DIR2_tph_communication_type,
	    CAST(DIR2_tph_country_prefix AS VARCHAR(10)) AS DIR2_tph_country_prefix,
		CAST(DIR2_TPH_NUMBER AS VARCHAR(20)) AS DIR2_TPH_NUMBER,
		CAST(CASE WHEN DIR2_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR2_DATE_OF_BIRTH, 3) ELSE DIR2_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR2_DATE_OF_BIRTH,
	    CAST(DIR2_address_type AS VARCHAR(10)) AS DIR2_address_type,
		CAST(DIR2_ADDRESS AS VARCHAR(99)) AS DIR2_ADDRESS,
	    CAST(DIR2_CITY AS VARCHAR(20)) AS DIR2_CITY,
	    CAST(DIR2_country_code AS VARCHAR(10)) AS DIR2_country_code,
	    CAST(DIR2_STATE AS VARCHAR(20)) AS DIR2_STATE,
		CAST(DIR2_OCCUPATION AS VARCHAR(99)) AS DIR2_OCCUPATION,
	    CAST(CASE WHEN DIR2_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR2_ROLE END AS VARCHAR(10)) AS DIR2_ROLE,
		------------------------------------- DIRECTOR 3 -----------------------------------------
		CAST(DIR3_GNDR AS VARCHAR(10)) AS DIR3_GNDR,
		CAST(DIR3_TITL AS VARCHAR(10)) AS DIR3_TITL,
		CAST(DIR3_FIRSTNAME AS VARCHAR(99)) AS DIR3_FIRSTNAME,
		CAST(DIR3_LASTNAME AS VARCHAR(99)) AS DIR3_LASTNAME,
		CAST(DIR3_FATHER_NAME AS VARCHAR(99)) AS DIR3_FATHER_NAME,
		CAST(DIR3_SSN_TYPE AS VARCHAR(10)) AS DIR3_SSN_TYPE,
		CAST(CASE WHEN DIR3_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR3_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR3_SSN,
	    CAST(DIR3_nationality1 AS VARCHAR(10)) AS DIR3_nationality1,
	    CAST(DIR3_Residence AS VARCHAR(10)) AS DIR3_Residence,
	    CAST(DIR3_tph_contact_type AS VARCHAR(10)) AS DIR3_tph_contact_type,
	    CAST(DIR3_tph_communication_type AS VARCHAR(10)) AS DIR3_tph_communication_type,
	    CAST(DIR3_tph_country_prefix AS VARCHAR(10)) AS DIR3_tph_country_prefix,
		CAST(DIR3_TPH_NUMBER AS VARCHAR(20)) AS DIR3_TPH_NUMBER,
		CAST(CASE WHEN DIR3_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR3_DATE_OF_BIRTH, 3) ELSE DIR3_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR3_DATE_OF_BIRTH,
	    CAST(DIR3_address_type AS VARCHAR(10)) AS DIR3_address_type,
		CAST(DIR3_ADDRESS AS VARCHAR(99)) AS DIR3_ADDRESS,
	    CAST(DIR3_CITY AS VARCHAR(20)) AS DIR3_CITY,
	    CAST(DIR3_country_code AS VARCHAR(10)) AS DIR3_country_code,
	    CAST(DIR3_STATE AS VARCHAR(20)) AS DIR3_STATE,
		CAST(DIR3_OCCUPATION AS VARCHAR(99)) AS DIR3_OCCUPATION,
	    CAST(CASE WHEN DIR3_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR3_ROLE END AS VARCHAR(10)) AS DIR3_ROLE,
		------------------------------------- DIRECTOR 4 -----------------------------------------
		CAST(DIR4_GNDR AS VARCHAR(10)) AS DIR4_GNDR,
		CAST(DIR4_TITL AS VARCHAR(10)) AS DIR4_TITL,
		CAST(DIR4_FIRSTNAME AS VARCHAR(99)) AS DIR4_FIRSTNAME,
		CAST(DIR4_LASTNAME AS VARCHAR(99)) AS DIR4_LASTNAME,
		CAST(DIR4_FATHER_NAME AS VARCHAR(99)) AS DIR4_FATHER_NAME,
		CAST(DIR4_SSN_TYPE AS VARCHAR(10)) AS DIR4_SSN_TYPE,
		CAST(CASE WHEN DIR4_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR4_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR4_SSN,
	    CAST(DIR4_nationality1 AS VARCHAR(10)) AS DIR4_nationality1,
	    CAST(DIR4_Residence AS VARCHAR(10)) AS DIR4_Residence,
	    CAST(DIR4_tph_contact_type AS VARCHAR(10)) AS DIR4_tph_contact_type,
	    CAST(DIR4_tph_communication_type AS VARCHAR(10)) AS DIR4_tph_communication_type,
	    CAST(DIR4_tph_country_prefix AS VARCHAR(10)) AS DIR4_tph_country_prefix,
		CAST(DIR4_TPH_NUMBER AS VARCHAR(20)) AS DIR4_TPH_NUMBER,
		CAST(CASE WHEN DIR4_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR4_DATE_OF_BIRTH, 3) ELSE DIR4_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR4_DATE_OF_BIRTH,
	    CAST(DIR4_address_type AS VARCHAR(10)) AS DIR4_address_type,
		CAST(DIR4_ADDRESS AS VARCHAR(99)) AS DIR4_ADDRESS,
	    CAST(DIR4_CITY AS VARCHAR(20)) AS DIR4_CITY,
	    CAST(DIR4_country_code AS VARCHAR(10)) AS DIR4_country_code,
	    CAST(DIR4_STATE AS VARCHAR(20)) AS DIR4_STATE,
		CAST(DIR4_OCCUPATION AS VARCHAR(99)) AS DIR4_OCCUPATION,
	    CAST(CASE WHEN DIR4_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR4_ROLE END AS VARCHAR(10)) AS DIR4_ROLE,
		------------------------------------- DIRECTOR 5 -----------------------------------------
		CAST(DIR5_GNDR AS VARCHAR(10)) AS DIR5_GNDR,
		CAST(DIR5_TITL AS VARCHAR(10)) AS DIR5_TITL,
		CAST(DIR5_FIRSTNAME AS VARCHAR(99)) AS DIR5_FIRSTNAME,
		CAST(DIR5_LASTNAME AS VARCHAR(99)) AS DIR5_LASTNAME,
		CAST(DIR5_FATHER_NAME AS VARCHAR(99)) AS DIR5_FATHER_NAME,
		CAST(DIR5_SSN_TYPE AS VARCHAR(10)) AS DIR5_SSN_TYPE,
		CAST(CASE WHEN DIR5_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR5_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR5_SSN,
	    CAST(DIR5_nationality1 AS VARCHAR(10)) AS DIR5_nationality1,
	    CAST(DIR5_Residence AS VARCHAR(10)) AS DIR5_Residence,
	    CAST(DIR5_tph_contact_type AS VARCHAR(10)) AS DIR5_tph_contact_type,
	    CAST(DIR5_tph_communication_type AS VARCHAR(10)) AS DIR5_tph_communication_type,
	    CAST(DIR5_tph_country_prefix AS VARCHAR(10)) AS DIR5_tph_country_prefix,
		CAST(DIR5_TPH_NUMBER AS VARCHAR(20)) AS DIR5_TPH_NUMBER,
		CAST(CASE WHEN DIR5_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR5_DATE_OF_BIRTH, 3) ELSE DIR5_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR5_DATE_OF_BIRTH,
	    CAST(DIR5_address_type AS VARCHAR(10)) AS DIR5_address_type,
		CAST(DIR5_ADDRESS AS VARCHAR(99)) AS DIR5_ADDRESS,
	    CAST(DIR5_CITY AS VARCHAR(20)) AS DIR5_CITY,
	    CAST(DIR5_country_code AS VARCHAR(10)) AS DIR5_country_code,
	    CAST(DIR5_STATE AS VARCHAR(20)) AS DIR5_STATE,
		CAST(DIR5_OCCUPATION AS VARCHAR(99)) AS DIR5_OCCUPATION,
	    CAST(CASE WHEN DIR5_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR5_ROLE END AS VARCHAR(10)) AS DIR5_ROLE,
		------------------------------------- DIRECTOR 6 -----------------------------------------
		CAST(DIR6_GNDR AS VARCHAR(10)) AS DIR6_GNDR,
		CAST(DIR6_TITL AS VARCHAR(10)) AS DIR6_TITL,
		CAST(DIR6_FIRSTNAME AS VARCHAR(99)) AS DIR6_FIRSTNAME,
		CAST(DIR6_LASTNAME AS VARCHAR(99)) AS DIR6_LASTNAME,
		CAST(DIR6_FATHER_NAME AS VARCHAR(99)) AS DIR6_FATHER_NAME,
		CAST(DIR6_SSN_TYPE AS VARCHAR(10)) AS DIR6_SSN_TYPE,
		CAST(CASE WHEN DIR6_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR6_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR6_SSN,
	    CAST(DIR6_nationality1 AS VARCHAR(10)) AS DIR6_nationality1,
	    CAST(DIR6_Residence AS VARCHAR(10)) AS DIR6_Residence,
	    CAST(DIR6_tph_contact_type AS VARCHAR(10)) AS DIR6_tph_contact_type,
	    CAST(DIR6_tph_communication_type AS VARCHAR(10)) AS DIR6_tph_communication_type,
	    CAST(DIR6_tph_country_prefix AS VARCHAR(10)) AS DIR6_tph_country_prefix,
		CAST(DIR6_TPH_NUMBER AS VARCHAR(20)) AS DIR6_TPH_NUMBER,
		CAST(CASE WHEN DIR6_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR6_DATE_OF_BIRTH, 3) ELSE DIR6_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR6_DATE_OF_BIRTH,
	    CAST(DIR6_address_type AS VARCHAR(10)) AS DIR6_address_type,
		CAST(DIR6_ADDRESS AS VARCHAR(99)) AS DIR6_ADDRESS,
	    CAST(DIR6_CITY AS VARCHAR(20)) AS DIR6_CITY,
	    CAST(DIR6_country_code AS VARCHAR(10)) AS DIR6_country_code,
	    CAST(DIR6_STATE AS VARCHAR(20)) AS DIR6_STATE,
		CAST(DIR6_OCCUPATION AS VARCHAR(99)) AS DIR6_OCCUPATION,
	    CAST(CASE WHEN DIR6_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR6_ROLE END AS VARCHAR(10)) AS DIR6_ROLE,
		------------------------------------- DIRECTOR 7 -----------------------------------------
		CAST(DIR7_GNDR AS VARCHAR(10)) AS DIR7_GNDR,
		CAST(DIR7_TITL AS VARCHAR(10)) AS DIR7_TITL,
		CAST(DIR7_FIRSTNAME AS VARCHAR(99)) AS DIR7_FIRSTNAME,
		CAST(DIR7_LASTNAME AS VARCHAR(99)) AS DIR7_LASTNAME,
		CAST(DIR7_FATHER_NAME AS VARCHAR(99)) AS DIR7_FATHER_NAME,
		CAST(DIR7_SSN_TYPE AS VARCHAR(10)) AS DIR7_SSN_TYPE,
		CAST(CASE WHEN DIR7_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR7_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR7_SSN,
	    CAST(DIR7_nationality1 AS VARCHAR(10)) AS DIR7_nationality1,
	    CAST(DIR7_Residence AS VARCHAR(10)) AS DIR7_Residence,
	    CAST(DIR7_tph_contact_type AS VARCHAR(10)) AS DIR7_tph_contact_type,
	    CAST(DIR7_tph_communication_type AS VARCHAR(10)) AS DIR7_tph_communication_type,
	    CAST(DIR7_tph_country_prefix AS VARCHAR(10)) AS DIR7_tph_country_prefix,
		CAST(DIR7_TPH_NUMBER AS VARCHAR(20)) AS DIR7_TPH_NUMBER,
		CAST(CASE WHEN DIR7_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR7_DATE_OF_BIRTH, 3) ELSE DIR7_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR7_DATE_OF_BIRTH,
	    CAST(DIR7_address_type AS VARCHAR(10)) AS DIR7_address_type,
		CAST(DIR7_ADDRESS AS VARCHAR(99)) AS DIR7_ADDRESS,
	    CAST(DIR7_CITY AS VARCHAR(20)) AS DIR7_CITY,
	    CAST(DIR7_country_code AS VARCHAR(10)) AS DIR7_country_code,
	    CAST(DIR7_STATE AS VARCHAR(20)) AS DIR7_STATE,
		CAST(DIR7_OCCUPATION AS VARCHAR(99)) AS DIR7_OCCUPATION,
	    CAST(CASE WHEN DIR7_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR7_ROLE END AS VARCHAR(10)) AS DIR7_ROLE,
		------------------------------------- DIRECTOR 8 -----------------------------------------
		CAST(DIR8_GNDR AS VARCHAR(10)) AS DIR8_GNDR,
		CAST(DIR8_TITL AS VARCHAR(10)) AS DIR8_TITL,
		CAST(DIR8_FIRSTNAME AS VARCHAR(99)) AS DIR8_FIRSTNAME,
		CAST(DIR8_LASTNAME AS VARCHAR(99)) AS DIR8_LASTNAME,
		CAST(DIR8_FATHER_NAME AS VARCHAR(99)) AS DIR8_FATHER_NAME,
		CAST(DIR8_SSN_TYPE AS VARCHAR(10)) AS DIR8_SSN_TYPE,
		CAST(CASE WHEN DIR8_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR8_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR8_SSN,
	    CAST(DIR8_nationality1 AS VARCHAR(10)) AS DIR8_nationality1,
	    CAST(DIR8_Residence AS VARCHAR(10)) AS DIR8_Residence,
	    CAST(DIR8_tph_contact_type AS VARCHAR(10)) AS DIR8_tph_contact_type,
	    CAST(DIR8_tph_communication_type AS VARCHAR(10)) AS DIR8_tph_communication_type,
	    CAST(DIR8_tph_country_prefix AS VARCHAR(10)) AS DIR8_tph_country_prefix,
		CAST(DIR8_TPH_NUMBER AS VARCHAR(20)) AS DIR8_TPH_NUMBER,
		CAST(CASE WHEN DIR8_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR8_DATE_OF_BIRTH, 3) ELSE DIR8_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR8_DATE_OF_BIRTH,
	    CAST(DIR8_address_type AS VARCHAR(10)) AS DIR8_address_type,
		CAST(DIR8_ADDRESS AS VARCHAR(99)) AS DIR8_ADDRESS,
	    CAST(DIR8_CITY AS VARCHAR(20)) AS DIR8_CITY,
	    CAST(DIR8_country_code AS VARCHAR(10)) AS DIR8_country_code,
	    CAST(DIR8_STATE AS VARCHAR(20)) AS DIR8_STATE,
		CAST(DIR8_OCCUPATION AS VARCHAR(99)) AS DIR8_OCCUPATION,
	    CAST(CASE WHEN DIR8_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR8_ROLE END AS VARCHAR(10)) AS DIR8_ROLE,
		------------------------------------- DIRECTOR 9 -----------------------------------------
		CAST(DIR9_GNDR AS VARCHAR(10)) AS DIR9_GNDR,
		CAST(DIR9_TITL AS VARCHAR(10)) AS DIR9_TITL,
		CAST(DIR9_FIRSTNAME AS VARCHAR(99)) AS DIR9_FIRSTNAME,
		CAST(DIR9_LASTNAME AS VARCHAR(99)) AS DIR9_LASTNAME,
		CAST(DIR9_FATHER_NAME AS VARCHAR(99)) AS DIR9_FATHER_NAME,
		CAST(DIR9_SSN_TYPE AS VARCHAR(10)) AS DIR9_SSN_TYPE,
		CAST(CASE WHEN DIR9_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR9_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR9_SSN,
	    CAST(DIR9_nationality1 AS VARCHAR(10)) AS DIR9_nationality1,
	    CAST(DIR9_Residence AS VARCHAR(10)) AS DIR9_Residence,
	    CAST(DIR9_tph_contact_type AS VARCHAR(10)) AS DIR9_tph_contact_type,
	    CAST(DIR9_tph_communication_type AS VARCHAR(10)) AS DIR9_tph_communication_type,
	    CAST(DIR9_tph_country_prefix AS VARCHAR(10)) AS DIR9_tph_country_prefix,
		CAST(DIR9_TPH_NUMBER AS VARCHAR(20)) AS DIR9_TPH_NUMBER,
		CAST(CASE WHEN DIR9_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR9_DATE_OF_BIRTH, 3) ELSE DIR9_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR9_DATE_OF_BIRTH,
	    CAST(DIR9_address_type AS VARCHAR(10)) AS DIR9_address_type,
		CAST(DIR9_ADDRESS AS VARCHAR(99)) AS DIR9_ADDRESS,
	    CAST(DIR9_CITY AS VARCHAR(20)) AS DIR9_CITY,
	    CAST(DIR9_country_code AS VARCHAR(10)) AS DIR9_country_code,
	    CAST(DIR9_STATE AS VARCHAR(20)) AS DIR9_STATE,
		CAST(DIR9_OCCUPATION AS VARCHAR(99)) AS DIR9_OCCUPATION,
	    CAST(CASE WHEN DIR9_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR9_ROLE END AS VARCHAR(10)) AS DIR9_ROLE,
		------------------------------------- DIRECTOR 10 -----------------------------------------
		CAST(DIR10_GNDR AS VARCHAR(10)) AS DIR10_GNDR,
		CAST(DIR10_TITL AS VARCHAR(10)) AS DIR10_TITL,
		CAST(DIR10_FIRSTNAME AS VARCHAR(99)) AS DIR10_FIRSTNAME,
		CAST(DIR10_LASTNAME AS VARCHAR(99)) AS DIR10_LASTNAME,
		CAST(DIR10_FATHER_NAME AS VARCHAR(99)) AS DIR10_FATHER_NAME,
		CAST(DIR10_SSN_TYPE AS VARCHAR(10)) AS DIR10_SSN_TYPE,
		CAST(CASE WHEN DIR10_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR10_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR10_SSN,
	    CAST(DIR10_nationality1 AS VARCHAR(10)) AS DIR10_nationality1,
	    CAST(DIR10_Residence AS VARCHAR(10)) AS DIR10_Residence,
	    CAST(DIR10_tph_contact_type AS VARCHAR(10)) AS DIR10_tph_contact_type,
	    CAST(DIR10_tph_communication_type AS VARCHAR(10)) AS DIR10_tph_communication_type,
	    CAST(DIR10_tph_country_prefix AS VARCHAR(10)) AS DIR10_tph_country_prefix,
		CAST(DIR10_TPH_NUMBER AS VARCHAR(20)) AS DIR10_TPH_NUMBER,
		CAST(CASE WHEN DIR10_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR10_DATE_OF_BIRTH, 3) ELSE DIR10_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR10_DATE_OF_BIRTH,
	    CAST(DIR10_address_type AS VARCHAR(10)) AS DIR10_address_type,
		CAST(DIR10_ADDRESS AS VARCHAR(99)) AS DIR10_ADDRESS,
	    CAST(DIR10_CITY AS VARCHAR(20)) AS DIR10_CITY,
	    CAST(DIR10_country_code AS VARCHAR(10)) AS DIR10_country_code,
	    CAST(DIR10_STATE AS VARCHAR(20)) AS DIR10_STATE,
		CAST(DIR10_OCCUPATION AS VARCHAR(99)) AS DIR10_OCCUPATION,
	    CAST(CASE WHEN DIR10_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR10_ROLE END AS VARCHAR(10)) AS DIR10_ROLE,
		------------------------------------------------ TAX NUM --------------------------------------------------------
		CAST(TMC_TAX_NUM AS VARCHAR(99)) AS TTMC_TAX_NUM,
		--------------------------------------------- SIGNATORY 1 ----------------------------------------------------
	    CAST(SIGNATORY1_IS_PRIMARY AS VARCHAR(10)) AS SIGNATORY1_IS_PRIMARY,
		CAST(SIGNATORY1_GNDR AS VARCHAR(10)) AS SIGNATORY1_GNDR,
		CAST(SIGNATORY1_TITL AS VARCHAR(10)) AS SIGNATORY1_TITL,
		CAST(SIGNATORY1_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY1_FIRSTNAME,
		CAST(SIGNATORY1_LASTNAME AS VARCHAR(99)) AS SIGNATORY1_LASTNAME,
		CAST(SIGNATORY1_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY1_FATHER_NAME,
		CAST(SIGNATORY1_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY1_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY1_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY1_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY1_SSN,   
	    CAST(SIGNATORY1_nationality1 AS VARCHAR(10)) AS SIGNATORY1_nationality1,
	    CAST(SIGNATORY1_Residence AS VARCHAR(10)) AS SIGNATORY1_Residence,
	    CAST(SIGNATORY1_tph_contact_type AS VARCHAR(10)) AS SIGNATORY1_tph_contact_type,
	    CAST(SIGNATORY1_tph_communication_type AS VARCHAR(10)) AS SIGNATORY1_tph_communication_type,	
	    CAST(SIGNATORY1_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY1_tph_country_prefix,
		CAST(CASE WHEN SIGNATORY1_TPH_NUMBER IS NULL OR SIGNATORY1_TPH_NUMBER = '' THEN 
                  COALESCE(CASE WHEN DIR1_TPH_NUMBER IS NULL OR DIR1_TPH_NUMBER = '' THEN TTMC_tph_number END, DIR1_TPH_NUMBER ) ELSE SIGNATORY1_TPH_NUMBER END AS VARCHAR(50)) AS SIGNATORY1_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY1_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY1_DATE_OF_BIRTH, 3) ELSE SIGNATORY1_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY1_DATE_OF_BIRTH,
	    CAST(SIGNATORY1_address_type AS VARCHAR(20)) AS SIGNATORY1_address_type,
		CAST(SIGNATORY1_ADDRESS AS VARCHAR(99)) AS SIGNATORY1_ADDRESS,
	    CAST(SIGNATORY1_CITY AS VARCHAR(20)) AS SIGNATORY1_CITY,
	    CAST(SIGNATORY1_country_code AS VARCHAR(10)) AS SIGNATORY1_country_code,
	    CAST(SIGNATORY1_STATE AS VARCHAR(20)) AS SIGNATORY1_STATE,
		CAST(SIGNATORY1_OCCUPATION AS VARCHAR(99)) AS SIGNATORY1_OCCUPATION,
	    CAST(SIGNATORY1_ROLE AS VARCHAR(10)) AS SIGNATORY1_ROLE,
		--------------------------------------------- SIGNATORY 2 ----------------------------------------------------
	    CAST(CASE WHEN SIGNATORY2_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY2_IS_PRIMARY END AS VARCHAR(10)) AS SIGNATORY2_IS_PRIMARY,
		CAST(SIGNATORY2_GNDR AS VARCHAR(10)) AS SIGNATORY2_GNDR,
		CAST(SIGNATORY2_TITL AS VARCHAR(10)) AS SIGNATORY2_TITL,
		CAST(SIGNATORY2_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY2_FIRSTNAME,
		CAST(SIGNATORY2_LASTNAME AS VARCHAR(99)) AS SIGNATORY2_LASTNAME,
		CAST(SIGNATORY2_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY2_FATHER_NAME,
		CAST(SIGNATORY2_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY2_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY2_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY2_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY2_SSN,
	    CAST(SIGNATORY2_nationality1 AS VARCHAR(10)) AS SIGNATORY2_nationality1,
	    CAST(SIGNATORY2_Residence AS VARCHAR(10)) AS SIGNATORY2_Residence,
	    CAST(SIGNATORY2_tph_contact_type AS VARCHAR(10)) AS SIGNATORY2_tph_contact_type,
	    CAST(SIGNATORY2_tph_communication_type AS VARCHAR(10)) AS SIGNATORY2_tph_communication_type,	
	    CAST(SIGNATORY2_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY2_tph_country_prefix,
		CAST(SIGNATORY2_TPH_NUMBER AS VARCHAR(50)) AS SIGNATORY2_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY2_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY2_DATE_OF_BIRTH, 3) ELSE SIGNATORY2_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY2_DATE_OF_BIRTH,
	    CAST(SIGNATORY2_address_type AS VARCHAR(20)) AS SIGNATORY2_address_type,
		CAST(SIGNATORY2_ADDRESS AS VARCHAR(99)) AS SIGNATORY2_ADDRESS,
	    CAST(SIGNATORY2_CITY AS VARCHAR(20)) AS SIGNATORY2_CITY,
	    CAST(SIGNATORY2_country_code AS VARCHAR(10)) AS SIGNATORY2_country_code,
	    CAST(SIGNATORY2_STATE AS VARCHAR(20)) AS SIGNATORY2_STATE,
		CAST(SIGNATORY2_OCCUPATION AS VARCHAR(99)) AS SIGNATORY2_OCCUPATION,
	    CAST(CASE WHEN SIGNATORY2_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY2_ROLE END AS VARCHAR(10)) AS SIGNATORY2_ROLE,
        --------------------------------------------- SIGNATORY 3 ----------------------------------------------------
	    CAST(CASE WHEN SIGNATORY3_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY3_IS_PRIMARY END AS VARCHAR(10)) AS SIGNATORY3_IS_PRIMARY,
		CAST(SIGNATORY3_GNDR AS VARCHAR(10)) AS SIGNATORY3_GNDR,
		CAST(SIGNATORY3_TITL AS VARCHAR(10)) AS SIGNATORY3_TITL,
		CAST(SIGNATORY3_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY3_FIRSTNAME,
		CAST(SIGNATORY3_LASTNAME AS VARCHAR(99)) AS SIGNATORY3_LASTNAME,
		CAST(SIGNATORY3_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY3_FATHER_NAME,
		CAST(SIGNATORY3_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY3_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY3_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY3_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY3_SSN,
	    CAST(SIGNATORY3_nationality1 AS VARCHAR(10)) AS SIGNATORY3_nationality1,
	    CAST(SIGNATORY3_Residence AS VARCHAR(10)) AS SIGNATORY3_Residence,
	    CAST(SIGNATORY3_tph_contact_type AS VARCHAR(10)) AS SIGNATORY3_tph_contact_type,
	    CAST(SIGNATORY3_tph_communication_type AS VARCHAR(10)) AS SIGNATORY3_tph_communication_type,	
	    CAST(SIGNATORY3_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY3_tph_country_prefix,
		CAST(SIGNATORY3_TPH_NUMBER AS VARCHAR(50)) AS SIGNATORY3_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY3_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY3_DATE_OF_BIRTH, 3) ELSE SIGNATORY3_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY3_DATE_OF_BIRTH,
	    CAST(SIGNATORY3_address_type AS VARCHAR(20)) AS SIGNATORY3_address_type,
		CAST(SIGNATORY3_ADDRESS AS VARCHAR(99)) AS SIGNATORY3_ADDRESS,
	    CAST(SIGNATORY3_CITY AS VARCHAR(20)) AS SIGNATORY3_CITY,
	    CAST(SIGNATORY3_country_code AS VARCHAR(10)) AS SIGNATORY3_country_code,
	    CAST(SIGNATORY3_STATE AS VARCHAR(20)) AS SIGNATORY3_STATE,
		CAST(SIGNATORY3_OCCUPATION AS VARCHAR(99)) AS SIGNATORY3_OCCUPATION,
	    CAST(CASE WHEN SIGNATORY3_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY3_ROLE END AS VARCHAR(10)) AS SIGNATORY3_ROLE,
		--------------------------------------------- SIGNATORY 4 ----------------------------------------------------
	    CAST(CASE WHEN SIGNATORY4_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY4_IS_PRIMARY END AS VARCHAR(10)) AS SIGNATORY4_IS_PRIMARY,
		CAST(SIGNATORY4_GNDR AS VARCHAR(10)) AS SIGNATORY4_GNDR,
		CAST(SIGNATORY4_TITL AS VARCHAR(10)) AS SIGNATORY4_TITL,
		CAST(SIGNATORY4_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY4_FIRSTNAME,
		CAST(SIGNATORY4_LASTNAME AS VARCHAR(99)) AS SIGNATORY4_LASTNAME,
		CAST(SIGNATORY4_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY4_FATHER_NAME,
		CAST(SIGNATORY4_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY4_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY4_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY4_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY4_SSN,
	    CAST(SIGNATORY4_nationality1 AS VARCHAR(10)) AS SIGNATORY4_nationality1,
	    CAST(SIGNATORY4_Residence AS VARCHAR(10)) AS SIGNATORY4_Residence,
	    CAST(SIGNATORY4_tph_contact_type AS VARCHAR(10)) AS SIGNATORY4_tph_contact_type,
	    CAST(SIGNATORY4_tph_communication_type AS VARCHAR(10)) AS SIGNATORY4_tph_communication_type,	
	    CAST(SIGNATORY4_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY4_tph_country_prefix,
		CAST(SIGNATORY4_TPH_NUMBER AS VARCHAR(50)) AS SIGNATORY4_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY4_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY4_DATE_OF_BIRTH, 3) ELSE SIGNATORY4_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY4_DATE_OF_BIRTH,
	    CAST(SIGNATORY4_address_type AS VARCHAR(20)) AS SIGNATORY4_address_type,
		CAST(SIGNATORY4_ADDRESS AS VARCHAR(99)) AS SIGNATORY4_ADDRESS,
	    CAST(SIGNATORY4_CITY AS VARCHAR(20)) AS SIGNATORY4_CITY,
	    CAST(SIGNATORY4_country_code AS VARCHAR(10)) AS SIGNATORY4_country_code,
	    CAST(SIGNATORY4_STATE AS VARCHAR(20)) AS SIGNATORY4_STATE,
		CAST(SIGNATORY4_OCCUPATION AS VARCHAR(99)) AS SIGNATORY4_OCCUPATION,
	    CAST(CASE WHEN SIGNATORY4_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY4_ROLE END AS VARCHAR(10)) AS SIGNATORY4_ROLE,
		--------------------------------------------- SIGNATORY 5 ----------------------------------------------------
	    CAST(CASE WHEN SIGNATORY5_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY5_IS_PRIMARY END AS VARCHAR(10)) AS SIGNATORY5_IS_PRIMARY,
		CAST(SIGNATORY5_GNDR AS VARCHAR(10)) AS SIGNATORY5_GNDR,
		CAST(SIGNATORY5_TITL AS VARCHAR(10)) AS SIGNATORY5_TITL,
		CAST(SIGNATORY5_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY5_FIRSTNAME,
		CAST(SIGNATORY5_LASTNAME AS VARCHAR(99)) AS SIGNATORY5_LASTNAME,
		CAST(SIGNATORY5_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY5_FATHER_NAME,
		CAST(SIGNATORY5_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY5_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY5_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY5_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY5_SSN,
	    CAST(SIGNATORY5_nationality1 AS VARCHAR(10)) AS SIGNATORY5_nationality1,
	    CAST(SIGNATORY5_Residence AS VARCHAR(10)) AS SIGNATORY5_Residence,
	    CAST(SIGNATORY5_tph_contact_type AS VARCHAR(10)) AS SIGNATORY5_tph_contact_type,
	    CAST(SIGNATORY5_tph_communication_type AS VARCHAR(10)) AS SIGNATORY5_tph_communication_type,	
	    CAST(SIGNATORY5_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY5_tph_country_prefix,
		CAST(SIGNATORY5_TPH_NUMBER AS VARCHAR(50)) AS SIGNATORY5_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY5_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY5_DATE_OF_BIRTH, 3) ELSE SIGNATORY5_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY5_DATE_OF_BIRTH,
	    CAST(SIGNATORY5_address_type AS VARCHAR(20)) AS SIGNATORY5_address_type,
		CAST(SIGNATORY5_ADDRESS AS VARCHAR(99)) AS SIGNATORY5_ADDRESS,
	    CAST(SIGNATORY5_CITY AS VARCHAR(20)) AS SIGNATORY5_CITY,
	    CAST(SIGNATORY5_country_code AS VARCHAR(10)) AS SIGNATORY5_country_code,
	    CAST(SIGNATORY5_STATE AS VARCHAR(20)) AS SIGNATORY5_STATE,
		CAST(SIGNATORY5_OCCUPATION AS VARCHAR(99)) AS SIGNATORY5_OCCUPATION,
	    CAST(CASE WHEN SIGNATORY5_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY5_ROLE END AS VARCHAR(10)) AS SIGNATORY5_ROLE,
		--------------------------------------------- SIGNATORY 6 ----------------------------------------------------
	    CAST(CASE WHEN SIGNATORY6_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY6_IS_PRIMARY END AS VARCHAR(10)) AS SIGNATORY6_IS_PRIMARY,
		CAST(SIGNATORY6_GNDR AS VARCHAR(10)) AS SIGNATORY6_GNDR,
		CAST(SIGNATORY6_TITL AS VARCHAR(10)) AS SIGNATORY6_TITL,
		CAST(SIGNATORY6_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY6_FIRSTNAME,
		CAST(SIGNATORY6_LASTNAME AS VARCHAR(99)) AS SIGNATORY6_LASTNAME,
		CAST(SIGNATORY6_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY6_FATHER_NAME,
		CAST(SIGNATORY6_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY6_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY6_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY6_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY6_SSN,
	    CAST(SIGNATORY6_nationality1 AS VARCHAR(10)) AS SIGNATORY6_nationality1,
	    CAST(SIGNATORY6_Residence AS VARCHAR(10)) AS SIGNATORY6_Residence,
	    CAST(SIGNATORY6_tph_contact_type AS VARCHAR(10)) AS SIGNATORY6_tph_contact_type,
	    CAST(SIGNATORY6_tph_communication_type AS VARCHAR(10)) AS SIGNATORY6_tph_communication_type,	
	    CAST(SIGNATORY6_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY6_tph_country_prefix,
		CAST(SIGNATORY6_TPH_NUMBER AS VARCHAR(50)) AS SIGNATORY6_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY6_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY6_DATE_OF_BIRTH, 3) ELSE SIGNATORY6_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY6_DATE_OF_BIRTH,
	    CAST(SIGNATORY6_address_type AS VARCHAR(20)) AS SIGNATORY6_address_type,
		CAST(SIGNATORY6_ADDRESS AS VARCHAR(99)) AS SIGNATORY6_ADDRESS,
	    CAST(SIGNATORY6_CITY AS VARCHAR(20)) AS SIGNATORY6_CITY,
	    CAST(SIGNATORY6_country_code AS VARCHAR(10)) AS SIGNATORY6_country_code,
	    CAST(SIGNATORY6_STATE AS VARCHAR(20)) AS SIGNATORY6_STATE,
		CAST(SIGNATORY6_OCCUPATION AS VARCHAR(99)) AS SIGNATORY6_OCCUPATION,
	    CAST(CASE WHEN SIGNATORY6_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY6_ROLE END AS VARCHAR(10)) AS SIGNATORY6_ROLE,
		--------------------------------------------- SIGNATORY 7 ----------------------------------------------------
	    CAST(CASE WHEN SIGNATORY7_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY7_IS_PRIMARY END AS VARCHAR(10)) AS SIGNATORY7_IS_PRIMARY,
		CAST(SIGNATORY7_GNDR AS VARCHAR(10)) AS SIGNATORY7_GNDR,
		CAST(SIGNATORY7_TITL AS VARCHAR(10)) AS SIGNATORY7_TITL,
		CAST(SIGNATORY7_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY7_FIRSTNAME,
		CAST(SIGNATORY7_LASTNAME AS VARCHAR(99)) AS SIGNATORY7_LASTNAME,
		CAST(SIGNATORY7_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY7_FATHER_NAME,
		CAST(SIGNATORY7_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY7_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY7_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY7_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY7_SSN,
	    CAST(SIGNATORY7_nationality1 AS VARCHAR(10)) AS SIGNATORY7_nationality1,
	    CAST(SIGNATORY7_Residence AS VARCHAR(10)) AS SIGNATORY7_Residence,
	    CAST(SIGNATORY7_tph_contact_type AS VARCHAR(10)) AS SIGNATORY7_tph_contact_type,
	    CAST(SIGNATORY7_tph_communication_type AS VARCHAR(10)) AS SIGNATORY7_tph_communication_type,	
	    CAST(SIGNATORY7_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY7_tph_country_prefix,
		CAST(SIGNATORY7_TPH_NUMBER AS VARCHAR(50)) AS SIGNATORY7_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY7_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY7_DATE_OF_BIRTH, 3) ELSE SIGNATORY7_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY7_DATE_OF_BIRTH,
	    CAST(SIGNATORY7_address_type AS VARCHAR(20)) AS SIGNATORY7_address_type,
		CAST(SIGNATORY7_ADDRESS AS VARCHAR(99)) AS SIGNATORY7_ADDRESS,
	    CAST(SIGNATORY7_CITY AS VARCHAR(20)) AS SIGNATORY7_CITY,
	    CAST(SIGNATORY7_country_code AS VARCHAR(10)) AS SIGNATORY7_country_code,
	    CAST(SIGNATORY7_STATE AS VARCHAR(20)) AS SIGNATORY7_STATE,
		CAST(SIGNATORY7_OCCUPATION AS VARCHAR(99)) AS SIGNATORY7_OCCUPATION,
	    CAST(CASE WHEN SIGNATORY7_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY7_ROLE END AS VARCHAR(10)) AS SIGNATORY7_ROLE,
		--------------------------------------------- SIGNATORY 8 ----------------------------------------------------
	    CAST(CASE WHEN SIGNATORY8_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY8_IS_PRIMARY END AS VARCHAR(10)) AS SIGNATORY8_IS_PRIMARY,
		CAST(SIGNATORY8_GNDR AS VARCHAR(10)) AS SIGNATORY8_GNDR,
		CAST(SIGNATORY8_TITL AS VARCHAR(10)) AS SIGNATORY8_TITL,
		CAST(SIGNATORY8_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY8_FIRSTNAME,
		CAST(SIGNATORY8_LASTNAME AS VARCHAR(99)) AS SIGNATORY8_LASTNAME,
		CAST(SIGNATORY8_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY8_FATHER_NAME,
		CAST(SIGNATORY8_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY8_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY8_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY8_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY8_SSN,
	    CAST(SIGNATORY8_nationality1 AS VARCHAR(10)) AS SIGNATORY8_nationality1,
	    CAST(SIGNATORY8_Residence AS VARCHAR(10)) AS SIGNATORY8_Residence,
	    CAST(SIGNATORY8_tph_contact_type AS VARCHAR(10)) AS SIGNATORY8_tph_contact_type,
	    CAST(SIGNATORY8_tph_communication_type AS VARCHAR(10)) AS SIGNATORY8_tph_communication_type,	
	    CAST(SIGNATORY8_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY8_tph_country_prefix,
		CAST(SIGNATORY8_TPH_NUMBER AS VARCHAR(50)) AS SIGNATORY8_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY8_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY8_DATE_OF_BIRTH, 3) ELSE SIGNATORY8_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY8_DATE_OF_BIRTH,
	    CAST(SIGNATORY8_address_type AS VARCHAR(20)) AS SIGNATORY8_address_type,
		CAST(SIGNATORY8_ADDRESS AS VARCHAR(99)) AS SIGNATORY8_ADDRESS,
	    CAST(SIGNATORY8_CITY AS VARCHAR(20)) AS SIGNATORY8_CITY,
	    CAST(SIGNATORY8_country_code AS VARCHAR(10)) AS SIGNATORY8_country_code,
	    CAST(SIGNATORY8_STATE AS VARCHAR(20)) AS SIGNATORY8_STATE,
		CAST(SIGNATORY8_OCCUPATION AS VARCHAR(99)) AS SIGNATORY8_OCCUPATION,
	    CAST(CASE WHEN SIGNATORY8_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY8_ROLE END AS VARCHAR(10)) AS SIGNATORY8_ROLE,

		CAST(TTMC_open AS VARCHAR(20)) AS TTMC_open,
		CAST(TTMC_status_code AS VARCHAR(10)) AS TTMC_status_code,
		CAST(TTMC_to_country AS VARCHAR(10)) AS TTMC_to_country
		FROM Final_Chunk 
		)
		
		
		SELECT * FROM DATA_V1 
		WHERE CATEGORY = '{entity_individual_flag}';
		 
	
	
	
		"""
	return query


def get_cash_withdrawal_query_v2(trxn_date, entity_individual_flag):
	query = rf"""
	
	
	WITH ENTITY AS (
		SELECT
		FCT.TSACTN_ID,
		FCT.ACCT_SROGT_ID
		FROM DP_SDMVW_DFDN.FCT_RTAIL_BNK_TSACTN_VW FCT
		INNER JOIN DP_SDMVW_DFDN.DIM_RTAIL_BNK_ACCT_VW ACCT ON ACCT.ACCT_SROGT_ID = FCT.ACCT_SROGT_ID
		LEFT JOIN (select CURY_EDW_ID, EXCH_RATE as CCY_RATE FROM  DP_SDMVW_DFDN.FCT_CURY_EXCH_RATE_VW where BATCH_DT = '{trxn_date}') EXC
		ON FCT.CURY_EDW_ID = EXC.CURY_EDW_ID
		WHERE 1=1
		-- AND FCT.TSACTN_ID IN ()
		AND FCT.TSACTN_TYPE_EDW_ID IN ('0001','0201','0006')
		AND FCT.TSACTN_DT = '{trxn_date}'
		AND CASE WHEN EXC.CURY_EDW_ID IS NOT NULL THEN FCT.TSACTN_AMT * CCY_RATE ELSE FCT.TSACTN_AMT END >= '2000000'
		AND 
		( 
		ACCT.CUST_TYPE_EDW_ID IN ( '63','51','36','31','61','34','53','37','35','65','33','32','55','62','64','54','52') 
		OR
		EXISTS(
		SELECT 1 FROM DP_SDMVW_DFDN.DIM_CTR_Keywords_VW t 
		WHERE t.flag = 'NO' AND ACCT.ACCT_TITL LIKE '%' || t.keyword || '%'
		)
		OR 
		EXISTS(
		SELECT 1 FROM DP_SDMVW_DFDN.DIM_CTR_Keywords_VW t 
		WHERE t.flag = 'YES' AND REGEXP_INSTR(ACCT.ACCT_TITL, '(^|[^A-Z0-9])' || t.keyword || '([^A-Z0-9]|$)', 1,1,0, 'i') > 0
		)
		)
		AND FCT.CR_DR_IND = 'D'
		AND FCT.RVSL_SEQ_NUM IS NULL
		AND FCT.Reveral_IND = 'N'
		AND FCT.TRAC_ID IS NULL
		)

		,TRXNS AS (
		SELECT
		FCT.*, 
		CASE WHEN FCT.CURY_EDW_ID <> 'PKR' THEN FCT.CURY_EDW_ID ELSE CAST(NULL AS VARCHAR(10)) END AS FRGN_CCY,
		CASE WHEN FCT.CURY_EDW_ID <> 'PKR' THEN CAST(FCT.TSACTN_AMT AS INT) ELSE CAST(NULL AS VARCHAR(10)) END AS FRGN_TSACTN_AMT,
		CASE WHEN FCT.CURY_EDW_ID <> 'PKR' THEN EXC.CCY_RATE ELSE CAST(NULL AS VARCHAR(10)) END AS EXCHANGE_RATE,
		FCT.TSACTN_AMT * EXC.CCY_RATE AS FRGN_TSACTN_AMT_PKR,
		ACCT.JOIN_ACCT_FLG,
		ACCT.ACCT_TITL,
		ACCT.ACCT_SROGT_ID AS ACCOUNT_SROGT_ID, ACCT.CUST_TYPE_EDW_ID AS ACCOUNT_CUST_TYPE_EDW_ID , ACCT.CUST_SROGT_ID AS ACCT_CUST_SROGT_ID, ACCT.BRNCH_SROGT_ID AS ACCT_BRNCH_SROGT_ID ,
		ACCT.ACCT_ORIGNL_OPN_DT , ACCT.ACCT_DESC, ACCT.CURY_EDW_ID AS ACCT_CURY_EDW_ID,
		PROD.ACCT_TYPE_DESC,
		--PROD.CODE AS ACCT_TYPE_CODE ,
		CASE WHEN REGEXP_SIMILAR(UPPER(ACCT.ACCT_TITL), '.*(^|[^A-Z0-9])CDC([^A-Z0-9]|$).*') = 1 THEN 'ATSAV' ELSE PROD.CODE END AS ACCT_TYPE_CODE,
		COD.CATEGORY_TYPE_DESC,
		COD.CODE AS CATEGORY_TYPE_CODE,
		CASE WHEN E.ACCT_SROGT_ID IS NOT NULL THEN 'ENTITY' ELSE 'INDIVIDUAL' END AS CATEGORY
		
		FROM DP_SDMVW_DFDN.FCT_RTAIL_BNK_TSACTN_VW FCT
		INNER JOIN DP_SDMVW_DFDN.DIM_RTAIL_BNK_ACCT_VW ACCT ON ACCT.ACCT_SROGT_ID = FCT.ACCT_SROGT_ID
		LEFT JOIN ENTITY E ON FCT.TSACTN_ID = E.TSACTN_ID 
		LEFT JOIN DP_SDMT_DFDN.DIM_CTR_ACCT_TYPE prod ON ACCT.PROD_SROGT_ID = prod.ACCT_TYPE 
		LEFT JOIN DP_SDMT_DFDN.DIM_CTR_CATEGORY_CODES COD ON ACCT.CUST_TYPE_EDW_ID = COD.CATEGORY_TYPE
		LEFT JOIN (select CURY_EDW_ID, EXCH_RATE as CCY_RATE FROM  DP_SDMVW_DFDN.FCT_CURY_EXCH_RATE_VW where BATCH_DT = '{trxn_date}') EXC
		ON FCT.CURY_EDW_ID = EXC.CURY_EDW_ID
		WHERE 1=1
		-- AND FCT.TSACTN_ID IN ()
		AND FCT.TSACTN_TYPE_EDW_ID IN ('0001','0201','0006')
		AND FCT.TSACTN_DT = '{trxn_date}'
		AND CASE WHEN EXC.CURY_EDW_ID IS NOT NULL THEN FCT.TSACTN_AMT * CCY_RATE ELSE FCT.TSACTN_AMT END >= '2000000'
		AND FCT.CR_DR_IND = 'D'
		AND FCT.RVSL_SEQ_NUM IS NULL
		AND FCT.Reveral_IND = 'N'
		AND FCT.TRAC_ID IS NULL
		)
		

		-- DP_REPORTING_MART.TM_DM_MD_MANDATE_AUTHORIZE
		, ENTITY_SIGNATORY AS (
		SELECT x.*,
		ROW_NUMBER() OVER(PARTITION BY ACCT_SROGT_ID ORDER BY M_DT_OF_BIRTH DESC) AS M_RN
			FROM (
			SELECT
		    T.ACCT_SROGT_ID,
		    T.TSACTN_ID,
		    M.CLIENT_NO AS M_CLIENT_NO,
			'TRUE' AS M_IS_PRIMARY, 
			CASE 
				 WHEN MC.GNDR IS NOT NULL THEN MC.GNDR
				 WHEN MC.GNDR IS NULL THEN 
							CASE WHEN RIGHT(MC.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(MC.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'M' 
							WHEN RIGHT(MC.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(MC.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'F' 
							ELSE CAST(NULL AS VARCHAR(10)) END END AS M_GNDR,			
			CASE 
				 WHEN MC.TITL IS NOT NULL THEN MC.TITL
				 WHEN MC.TITL IS NULL THEN 
							CASE WHEN RIGHT(MC.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(MC.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'MR' 
							WHEN RIGHT(MC.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(MC.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'MS'
							ELSE CAST(NULL AS VARCHAR(10)) END END AS M_TITL, 			

		    TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
					FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) )  AS  M_FRST_NAME,
			
			CASE WHEN  REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0 
						THEN  TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
			              			  POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) )
						ELSE 
								CASE WHEN (MC.FRST_NAME IS NULL AND MC.MDL_NAME IS NULL AND MC.LAST_NAME IS NULL) OR (MC.FRST_NAME = '' AND MC.MDL_NAME = '' AND MC.LAST_NAME = '')
											THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
											 			FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
											ELSE 
													CASE WHEN REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(MC.FRST_NAME, '') || ' ' || COALESCE(MC.MDL_NAME, '') || ' ' || COALESCE(MC.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0
																THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(MC.FRST_NAME, '') || ' ' || COALESCE(MC.MDL_NAME, '') || ' ' || COALESCE(MC.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
												            				POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(MC.FRST_NAME, '') || ' ' || COALESCE(MC.MDL_NAME, '') || ' ' || COALESCE(MC.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) 
													ELSE TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
															 	FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
													END
								END
			END	AS M_LAST_NAME ,
			
		    TO_CHAR(MC.DT_OF_BIRTH , 'YYYY-MM-DD') ||  'T00:00:00' AS M_DT_OF_BIRTH,
			TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.FTHR_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) AS M_MOTHER_NAME,
			
			MC.IDNTFTN_TYPE_EDW_ID AS M_SSN_TYPE,
			CASE WHEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) = '' THEN CAST(NULL AS VARCHAR(10)) 
						   ELSE TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) END AS M_SSN,
		     CASE
				when MC.MBL_NUM is not null AND MC.MBL_NUM <> ''  
				THEN REGEXP_REPLACE(REGEXP_REPLACE(TRIM(MC.MBL_NUM), '[^0-9]', ''), '^(0092|[+]92|92|0)+', '')
		        when MC.PHN_RSDNC is not null AND MC.PHN_RSDNC <> '' then TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(MC.PHN_RSDNC), '[^ ]+', 1, 1), '[^0-9]', '') )
		        else 
				case 
					WHEN REGEXP_SIMILAR(MC.PHN_BUSN, '.*[A-Za-z].*') = '1' AND REGEXP_SIMILAR(MC.PHN_BUSN, '.*[0-9].*') = '1' THEN CAST(NULL AS VARCHAR(11))
					WHEN REGEXP_SIMILAR(MC.PHN_BUSN, '.*[A-Za-z].*') = '1' THEN CAST(NULL AS VARCHAR(11))
					ELSE 
						case
							when substr(regexp_replace(MC.PHN_BUSN, '[^0-9]', ''), 1,3) = '092' then substr(regexp_replace(MC.PHN_BUSN, '[^0-9]', ''), 3) 
							when substr(regexp_replace(MC.PHN_BUSN, '[^0-9]', ''), 1,2) = '92' then substr(regexp_replace(MC.PHN_BUSN, '[^0-9]', ''), 3)  
							ELSE trim(LEADING '0' FROM regexp_replace(MC.PHN_BUSN, '[^0-9]', ''))
						end
				end 
			END as M_tph_number,      	
			
			TRIM(OREPLACE(OREPLACE(
			CASE 
			WHEN TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is not null AND TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3
			              THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' ')  , '[[:space:]]+', ' '))  
			WHEN (TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
					       AND (TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
					      THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' ')) 
			WHEN (TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
					       AND ( TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
						   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(MC.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))
			WHEN (TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3 ) 
					       AND (TRIM(REGEXP_REPLACE(TRIM(MC.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(MC.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.OTH_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
						   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(MC.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))		   
			ELSE CAST(NULL AS VARCHAR(10)) 
			END
			,CHR(13),' '),CHR(10), ' ')) as M_address,

		    CASE WHEN _MDO.OCPTN_DESC IS NOT NULL OR _MDO.OCPTN_DESC <> '' THEN _MDO.OCPTN_DESC ELSE 'Others' END AS M_OCCUPATION,
			
			MC.CTRY_OF_NTLTY as M_nationality1,
			'PK' as M_Residence,
			CASE WHEN MC.MBL_NUM is not null AND MC.MBL_NUM <> '' then 'PAPVT' when MC.MBL_NUM is null OR MC.MBL_NUM = '' then 'PAOFF' END as M_tph_contact_type,
			CASE WHEN MC.MBL_NUM is not null AND MC.MBL_NUM <> '' then 'COMOB' else 'COLAN' END as M_tph_communication_type,
			'92' as M_tph_country_prefix,
			
			CASE WHEN MC.PERM_ADDR is not null and MC.PERM_ADDR <> '' then 'PAPVT' 
						when MC.PERM_ADDR is null OR MC.PERM_ADDR = '' then 'PAOFF' END as M_address_type,
						
			CASE WHEN TRIM(MC.RSDNTL_CITY)  = '0' THEN CAST(NULL AS VARCHAR(10)) ELSE MC.RSDNTL_CITY END AS M_city, 
			
			'PK' as M_country_code,
			CASE  
			when substr(MC.IDNTFTN_VAL,1,1) IN ('1', '2') then 'KHYBER-PAKHTUNKHWA'
			when substr(MC.IDNTFTN_VAL,1,1) IN ('3', '6') then 'PUNJAB'
			when substr(MC.IDNTFTN_VAL,1,1) = '4' then 'SINDH'
			when substr(MC.IDNTFTN_VAL,1,1) = '5' then 'BALOCHISTAN'
			when substr(MC.IDNTFTN_VAL,1,1) = '7' then 'GILGIT-BALISTAN'
			when substr(MC.IDNTFTN_VAL,1,1) = '8' then 'AZAD-KASHMIR'
			ELSE cast(null as varchar(10)) 
			END as M_state,
			
			'ARPYS' AS M_role
			
		    ,ROW_NUMBER() OVER(PARTITION BY M.CLIENT_NO ORDER BY M.CLIENT_NO) AS RN
	    FROM  TRXNS T
	    INNER JOIN DP_REPORTING_MART.TM_DM_MD_MANDATE_AUTHORIZE M ON T.ACCT_SROGT_ID = M.ACCT_NO  -- DP_SDMVW_DFDN.TM_DM_MD_MANDATE_AUTHORIZE_VW 
	    LEFT JOIN DP_SDMVW_DFDN.DIM_CUST_VW MC ON MC.CUST_SROGT_ID = M.CLIENT_NO AND MC.SYSTEM_CODE = 'CBS'
	    LEFT JOIN DP_SDMT_DFDN.DIM_OCPTN_SS _MDO ON MC.OCPTN_EDW_ID = _MDO.OCPTN_EDW_ID
	    WHERE 1=1 AND M.START_DATE = (SELECT CAST(MAX(START_DATE) AS DATE) AS START_DATE FROM DP_REPORTING_MART.TM_DM_MD_MANDATE_AUTHORIZE)
		 -- CAST(CURRENT_DATE - 1 AS DATE)
		 AND T.CATEGORY = 'ENTITY'
	
		) AS X
	WHERE 1=1
	AND X.RN = 1
	)

	, INDIVIDUAL_ACCTS_CUSTOMERS AS ( 
	SELECT DISTINCT
	T.ACCT_SROGT_ID, T.ACCT_CUST_SROGT_ID, T.JOIN_ACCT_FLG
	FROM TRXNS T -- DT_SDMT_UBL.CTR_TRXNS T
	WHERE 1=1 
	AND T.CATEGORY = 'INDIVIDUAL'

	UNION ALL

	SELECT DISTINCT
	T.ACCT_SROGT_ID, J.CUST_SROGT_ID AS ACCT_CUST_SROGT_ID , T.JOIN_ACCT_FLG
	FROM TRXNS T --DT_SDMT_UBL.CTR_TRXNS  T
	INNER JOIN DP_SDMT_DFDN.DIM_RTAIL_BNK_ACCT_JNT J ON T.ACCT_SROGT_ID = J.ACCT_SROGT_ID AND T.JOIN_ACCT_FLG = 1
	WHERE 1=1
	AND T.CATEGORY = 'INDIVIDUAL'
	)

	, INDIVIDUAL_SIGNATORY AS (
	SELECT DISTINCT 
    T.ACCT_SROGT_ID,
	--T.ACCT_TITL,
    T.TSACTN_ID,
    M.ACCT_CUST_SROGT_ID AS M_CLIENT_NO,
	-- T.JOIN_ACCT_FLG,
	'TRUE' AS M_IS_PRIMARY, 
	CASE 
		 WHEN MC.GNDR IS NOT NULL THEN MC.GNDR
		 WHEN MC.GNDR IS NULL THEN 
					CASE WHEN RIGHT(MC.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(MC.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'M' 
					WHEN RIGHT(MC.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(MC.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'F' 
					ELSE CAST(NULL AS VARCHAR(10)) END END AS M_GNDR,			
	CASE 
		 WHEN MC.TITL IS NOT NULL THEN MC.TITL
		 WHEN MC.TITL IS NULL THEN 
					CASE WHEN RIGHT(MC.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(MC.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'MR' 
					WHEN RIGHT(MC.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(MC.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'MS'
					ELSE CAST(NULL AS VARCHAR(10)) END END AS M_TITL, 			

    TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
			FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) )  AS  M_FRST_NAME,
	
	CASE WHEN  REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0 
				THEN  TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
	              			  POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) )
				ELSE 
						CASE WHEN (MC.FRST_NAME IS NULL AND MC.MDL_NAME IS NULL AND MC.LAST_NAME IS NULL) OR (MC.FRST_NAME = '' AND MC.MDL_NAME = '' AND MC.LAST_NAME = '')
									THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
									 			FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
									ELSE 
											CASE WHEN REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(MC.FRST_NAME, '') || ' ' || COALESCE(MC.MDL_NAME, '') || ' ' || COALESCE(MC.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0
														THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(MC.FRST_NAME, '') || ' ' || COALESCE(MC.MDL_NAME, '') || ' ' || COALESCE(MC.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
										            				POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(MC.FRST_NAME, '') || ' ' || COALESCE(MC.MDL_NAME, '') || ' ' || COALESCE(MC.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) 
											ELSE TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
													 	FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
											END
						END
	END	AS M_LAST_NAME ,
	
    TO_CHAR(MC.DT_OF_BIRTH , 'YYYY-MM-DD') ||  'T00:00:00' AS M_DT_OF_BIRTH,
	TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.FTHR_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) AS M_MOTHER_NAME,
	
	MC.IDNTFTN_TYPE_EDW_ID AS M_SSN_TYPE,
	CASE WHEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) = '' THEN CAST(NULL AS VARCHAR(10)) 
				   ELSE TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) END AS M_SSN,
     CASE
		when MC.MBL_NUM is not null AND MC.MBL_NUM <> ''  
		THEN REGEXP_REPLACE(REGEXP_REPLACE(TRIM(MC.MBL_NUM), '[^0-9]', ''), '^(0092|[+]92|92|0)+', '')
        when MC.PHN_RSDNC is not null AND MC.PHN_RSDNC <> '' then TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(MC.PHN_RSDNC), '[^ ]+', 1, 1), '[^0-9]', '') )
        else 
		case 
			WHEN REGEXP_SIMILAR(MC.PHN_BUSN, '.*[A-Za-z].*') = '1' AND REGEXP_SIMILAR(MC.PHN_BUSN, '.*[0-9].*') = '1' THEN CAST(NULL AS VARCHAR(11))
			WHEN REGEXP_SIMILAR(MC.PHN_BUSN, '.*[A-Za-z].*') = '1' THEN CAST(NULL AS VARCHAR(11))
			ELSE 
				case
					when substr(regexp_replace(MC.PHN_BUSN, '[^0-9]', ''), 1,3) = '092' then substr(regexp_replace(MC.PHN_BUSN, '[^0-9]', ''), 3) 
					when substr(regexp_replace(MC.PHN_BUSN, '[^0-9]', ''), 1,2) = '92' then substr(regexp_replace(MC.PHN_BUSN, '[^0-9]', ''), 3)  
					ELSE trim(LEADING '0' FROM regexp_replace(MC.PHN_BUSN, '[^0-9]', ''))
				end
		end 
	END as M_tph_number,      	
	
	TRIM(OREPLACE(OREPLACE(
	CASE 
	WHEN TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is not null AND TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3
	              THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' ')  , '[[:space:]]+', ' '))  
	WHEN (TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
			       AND (TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
			      THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' ')) 
	WHEN (TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
			       AND ( TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
				   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(MC.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))
	WHEN (TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3 ) 
			       AND (TRIM(REGEXP_REPLACE(TRIM(MC.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(MC.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.OTH_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
				   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(MC.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))		   
	ELSE CAST(NULL AS VARCHAR(10)) 
	END
	,CHR(13),' '),CHR(10), ' ')) as M_address,

    CASE WHEN _MDO.OCPTN_DESC IS NOT NULL OR _MDO.OCPTN_DESC <> '' THEN _MDO.OCPTN_DESC ELSE 'Others' END AS M_OCCUPATION,
	
	MC.CTRY_OF_NTLTY as M_nationality1,
	'PK' as M_Residence,
	CASE WHEN MC.MBL_NUM is not null AND MC.MBL_NUM <> '' then 'PAPVT' when MC.MBL_NUM is null OR MC.MBL_NUM = '' then 'PAOFF' END as M_tph_contact_type,
	CASE WHEN MC.MBL_NUM is not null AND MC.MBL_NUM <> '' then 'COMOB' else 'COLAN' END as M_tph_communication_type,
	'92' as M_tph_country_prefix,
	
	CASE WHEN MC.PERM_ADDR is not null and MC.PERM_ADDR <> '' then 'PAPVT' 
				when MC.PERM_ADDR is null OR MC.PERM_ADDR = '' then 'PAOFF' END as M_address_type,
				
	CASE WHEN TRIM(MC.RSDNTL_CITY)  = '0' THEN CAST(NULL AS VARCHAR(10)) ELSE MC.RSDNTL_CITY END AS M_city, 
	
	'PK' as M_country_code,
	CASE  
	when substr(MC.IDNTFTN_VAL,1,1) IN ('1', '2') then 'KHYBER-PAKHTUNKHWA'
	when substr(MC.IDNTFTN_VAL,1,1) IN ('3', '6') then 'PUNJAB'
	when substr(MC.IDNTFTN_VAL,1,1) = '4' then 'SINDH'
	when substr(MC.IDNTFTN_VAL,1,1) = '5' then 'BALOCHISTAN'
	when substr(MC.IDNTFTN_VAL,1,1) = '7' then 'GILGIT-BALISTAN'
	when substr(MC.IDNTFTN_VAL,1,1) = '8' then 'AZAD-KASHMIR'
	ELSE cast(null as varchar(10)) 
	END as M_state,
	
	'ARPYS' AS M_role
	
    -- ,ROW_NUMBER() OVER(PARTITION BY M.CLIENT_NO ORDER BY M.CLIENT_NO) AS RN
	FROM  TRXNS T --DT_SDMT_UBL.CTR_TRXNS T
	INNER JOIN INDIVIDUAL_ACCTS_CUSTOMERS M ON T.ACCT_SROGT_ID = M.ACCT_SROGT_ID  -- DP_SDMVW_DFDN.TM_DM_MD_MANDATE_AUTHORIZE_VW 
	LEFT JOIN DP_SDMVW_DFDN.DIM_CUST_VW MC ON MC.CUST_SROGT_ID = M.ACCT_CUST_SROGT_ID AND MC.SYSTEM_CODE = 'CBS'
	LEFT JOIN DP_SDMT_DFDN.DIM_OCPTN_SS _MDO ON MC.OCPTN_EDW_ID = _MDO.OCPTN_EDW_ID
		)


		, MANDATE AS (
		SELECT X.*,
		ROW_NUMBER() OVER(PARTITION BY ACCT_SROGT_ID ORDER BY M_DT_OF_BIRTH DESC) AS M_RN
		FROM (
				SELECT ACCT_SROGT_ID, /*TSACTN_ID,*/  M_CLIENT_NO, M_IS_PRIMARY, M_GNDR, M_TITL, M_FRST_NAME,
					M_LAST_NAME, M_DT_OF_BIRTH, M_MOTHER_NAME, M_SSN_TYPE, M_SSN, M_tph_number, M_address,
					M_OCCUPATION, M_nationality1, M_Residence, M_tph_contact_type, M_tph_communication_type, 
					M_tph_country_prefix, M_address_type, M_city, M_country_code, M_state, M_role
				FROM ENTITY_SIGNATORY
				UNION 
				SELECT ACCT_SROGT_ID, /*TSACTN_ID,*/  M_CLIENT_NO, M_IS_PRIMARY, M_GNDR, M_TITL, M_FRST_NAME,
					M_LAST_NAME, M_DT_OF_BIRTH, M_MOTHER_NAME, M_SSN_TYPE, M_SSN, M_tph_number, M_address,
					M_OCCUPATION, M_nationality1, M_Residence, M_tph_contact_type, M_tph_communication_type, 
					M_tph_country_prefix, M_address_type, M_city, M_country_code, M_state, M_role
				FROM INDIVIDUAL_SIGNATORY
		) AS X
		)
		
		
		-- DP_REPORTING_MART.FM_DIRECTOR_DTLS
		, DIRECTORS AS (
			SELECT x.*, ROW_NUMBER() OVER(PARTITION BY CUST_SROGT_ID ORDER BY D_DT_OF_BIRTH DESC) AS D_RN
			FROM (
				SELECT 
					T.ACCT_SROGT_ID,
					T.CUST_SROGT_ID,
					T.TSACTN_ID,
					DC.CUST_SROGT_ID AS D_CUST_SROGT_ID,
					
					CASE 
						WHEN DC.GNDR IS NOT NULL THEN DC.GNDR
						WHEN DC.GNDR IS NULL THEN 
									CASE WHEN RIGHT(DC.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(DC.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'M' 
									WHEN RIGHT(DC.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(DC.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'F' 
									ELSE CAST(NULL AS VARCHAR(10)) END END AS D_GNDR,			
					CASE 
						WHEN DC.TITL IS NOT NULL THEN DC.TITL
						WHEN DC.TITL IS NULL THEN 
									CASE WHEN RIGHT(DC.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(DC.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'MR' 
									WHEN RIGHT(DC.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(DC.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'MS'
									ELSE CAST(NULL AS VARCHAR(10)) END END AS D_TITL, 	

					TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
							FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) )  AS  D_FRST_NAME,
					
					CASE WHEN  REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0 
								THEN  TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
											POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) )
								ELSE 
										CASE WHEN (DC.FRST_NAME IS NULL AND DC.MDL_NAME IS NULL AND DC.LAST_NAME IS NULL) OR (DC.FRST_NAME = '' AND DC.MDL_NAME = '' AND DC.LAST_NAME = '')
													THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
																FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
													ELSE 
															CASE WHEN REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(DC.FRST_NAME, '') || ' ' || COALESCE(DC.MDL_NAME, '') || ' ' || COALESCE(DC.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0
																		THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(DC.FRST_NAME, '') || ' ' || COALESCE(DC.MDL_NAME, '') || ' ' || COALESCE(DC.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
																					POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(DC.FRST_NAME, '') || ' ' || COALESCE(DC.MDL_NAME, '') || ' ' || COALESCE(DC.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) 
															ELSE TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
																		FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
															END
										END
					END	AS D_LAST_NAME ,
					
					TO_CHAR(DC.DT_OF_BIRTH , 'YYYY-MM-DD') ||  'T00:00:00' AS D_DT_OF_BIRTH,
					TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.FTHR_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) AS D_MOTHER_NAME,
					
					DC.IDNTFTN_TYPE_EDW_ID AS D_SSN_TYPE,
					CASE WHEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) = '' THEN CAST(NULL AS VARCHAR(10)) 
								ELSE TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) END AS D_SSN,
					CASE
						when DC.MBL_NUM is not null AND DC.MBL_NUM <> ''  
						THEN REGEXP_REPLACE(REGEXP_REPLACE(TRIM(DC.MBL_NUM), '[^0-9]', ''), '^(0092|[+]92|92|0)+', '')
						when DC.PHN_RSDNC is not null AND DC.PHN_RSDNC <> '' then TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(DC.PHN_RSDNC), '[^ ]+', 1, 1), '[^0-9]', '') )
						else 
						case 
						WHEN REGEXP_SIMILAR(DC.PHN_BUSN, '.*[A-Za-z].*') = '1' AND REGEXP_SIMILAR(DC.PHN_BUSN, '.*[0-9].*') = '1' THEN CAST(NULL AS VARCHAR(11))
						WHEN REGEXP_SIMILAR(DC.PHN_BUSN, '.*[A-Za-z].*') = '1' THEN CAST(NULL AS VARCHAR(11))
						ELSE 
							case
								when substr(regexp_replace(DC.PHN_BUSN, '[^0-9]', ''), 1,3) = '092' then substr(regexp_replace(DC.PHN_BUSN, '[^0-9]', ''), 3) 
								when substr(regexp_replace(DC.PHN_BUSN, '[^0-9]', ''), 1,2) = '92' then substr(regexp_replace(DC.PHN_BUSN, '[^0-9]', ''), 3)  
								ELSE trim(LEADING '0' FROM regexp_replace(DC.PHN_BUSN, '[^0-9]', ''))
							end
					end 
				END as D_tph_number, 	
				
				TRIM(OREPLACE(OREPLACE(
				CASE 
				WHEN TRIM(REGEXP_REPLACE(TRIM(DC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is not null AND TRIM(REGEXP_REPLACE(TRIM(DC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(DC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3
				              THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(DC.PERM_ADDR), '[^A-Za-z0-9 ]', ' ')  , '[[:space:]]+', ' '))  
				WHEN (TRIM(REGEXP_REPLACE(TRIM(DC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(DC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(DC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
						       AND (TRIM(REGEXP_REPLACE(TRIM(DC.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(DC.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(DC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
						      THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(DC.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' ')) 
				WHEN (TRIM(REGEXP_REPLACE(TRIM(DC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(DC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(DC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
						       AND ( TRIM(REGEXP_REPLACE(TRIM(DC.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(DC.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(DC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(DC.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))
				WHEN (TRIM(REGEXP_REPLACE(TRIM(DC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(DC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(DC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3 ) 
						       AND (TRIM(REGEXP_REPLACE(TRIM(DC.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(DC.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(DC.OTH_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(DC.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))		   
				ELSE CAST(NULL AS VARCHAR(10)) 
				END
				,CHR(13),' '),CHR(10), ' ')) as D_address,	

				CASE WHEN _DDO.OCPTN_DESC IS NOT NULL OR _DDO.OCPTN_DESC <> '' THEN _DDO.OCPTN_DESC ELSE 'Others' END AS D_OCCUPATION,
				
				DC.CTRY_OF_NTLTY as D_nationality1,
				'PK' as D_Residence,
				CASE WHEN DC.MBL_NUM is not null AND DC.MBL_NUM <> '' then 'PAPVT' when DC.MBL_NUM is null OR DC.MBL_NUM = '' then 'PAOFF' END as D_tph_contact_type,
				CASE WHEN DC.MBL_NUM is not null AND DC.MBL_NUM <> '' then 'COMOB' else 'COLAN' END as D_tph_communication_type,
				'92' as D_tph_country_prefix,
				
				CASE WHEN DC.PERM_ADDR is not null and DC.PERM_ADDR <> '' then 'PAPVT' 
						    when DC.PERM_ADDR is null OR DC.PERM_ADDR = '' then 'PAOFF' END as D_address_type,
				
				CASE WHEN TRIM(DC.RSDNTL_CITY) = '0' THEN CAST(NULL AS VARCHAR(10)) ELSE DC.RSDNTL_CITY END AS D_city,  
				
				'PK' as D_country_code,
				CASE  
				when substr(DC.IDNTFTN_VAL,1,1) IN ('1', '2') then 'KHYBER-PAKHTUNKHWA'
				when substr(DC.IDNTFTN_VAL,1,1) IN ('3', '6') then 'PUNJAB'
				when substr(DC.IDNTFTN_VAL,1,1) = '4' then 'SINDH'
				when substr(DC.IDNTFTN_VAL,1,1) = '5' then 'BALOCHISTAN'
				when substr(DC.IDNTFTN_VAL,1,1) = '7' then 'GILGIT-BALISTAN'
				when substr(DC.IDNTFTN_VAL,1,1) = '8' then 'AZAD-KASHMIR'
				ELSE cast(null as varchar(10)) 
				END as D_state,
				
				'ERDIR' AS D_role
				
				,ROW_NUMBER() OVER(PARTITION BY DD.CLIENT_NO_DIR ORDER BY DD.CLIENT_NO_DIR) AS RN
			FROM TRXNS T
			INNER JOIN DP_REPORTING_MART.FM_DIRECTOR_DTLS DD ON T.CUST_SROGT_ID = DD.CLIENT_NO  -- DP_SDMVW_DFDN.FM_DIRECTOR_DTLS_VW 
			LEFT JOIN DP_SDMVW_DFDN.DIM_CUST_VW DC ON DC.CUST_SROGT_ID = DD.CLIENT_NO_DIR AND DC.SYSTEM_CODE = 'CBS' 
			LEFT JOIN DP_SDMT_DFDN.DIM_OCPTN_SS _DDO ON DC.OCPTN_EDW_ID = _DDO.OCPTN_EDW_ID
			WHERE 1=1 AND DD.START_DATE = (SELECT CAST(MAX(START_DATE) AS DATE) AS START_DATE FROM DP_REPORTING_MART.FM_DIRECTOR_DTLS)
			-- CAST(CURRENT_DATE - 1 AS DATE)
		) X 
	WHERE 1=1 
	AND X.RN = 1
		)
					
		, WALKIN_DETAILS AS (
		
		SELECT * FROM (
			select 
			w.Transaction_ID,
			CASE 
			 WHEN w.Cust_Type = 'AH' AND d.GNDR IS NOT NULL THEN d.GNDR
			 WHEN w.Cust_Type = 'AH' AND d.GNDR IS NULL THEN 
						CASE WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'M' 
						WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'F' 
						ELSE CAST(NULL AS VARCHAR(10)) END 
			 WHEN w.Cust_Type = 'TP' THEN
						CASE WHEN RIGHT(W_CNIC,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(W_CNIC, '-', ''), '/', '')) = 13 THEN 'M' 
						WHEN RIGHT(W_CNIC,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(W_CNIC, '-', ''), '/', '')) = 13  THEN 'F' 
						ELSE CAST(NULL AS VARCHAR(10)) END  
			END as Gender,

			CASE 
			 WHEN w.Cust_Type = 'AH' AND d.TITL IS NOT NULL THEN d.TITL
			 WHEN w.Cust_Type = 'AH' AND d.TITL IS NULL THEN 
						CASE WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'MR' 
						WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'MS'
						END 
			 WHEN w.Cust_Type = 'TP' THEN
						CASE WHEN RIGHT(W_CNIC,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(W_CNIC, '-', ''), '/', '')) = 13 THEN 'MR' 
						WHEN RIGHT(W_CNIC,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(W_CNIC, '-', ''), '/', '')) = 13  THEN 'MS' 
						ELSE CAST(NULL AS VARCHAR(10)) END  
			END as "Title",
			CASE 
			WHEN w.Cust_Type = 'AH'  THEN
			TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
							FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
			WHEN w.Cust_Type = 'TP'  THEN
			TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
							FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) )  
			END AS First_Name ,

			CASE 
			WHEN w.Cust_Type = 'AH'  THEN
				CASE WHEN  REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0 
							THEN  TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
				              			  POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) )
							ELSE 
									CASE WHEN (D.FRST_NAME IS NULL AND D.MDL_NAME IS NULL AND D.LAST_NAME IS NULL) OR (D.FRST_NAME = '' AND D.MDL_NAME = '' AND D.LAST_NAME = '')
												THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
												 			FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
												ELSE 
														CASE WHEN REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0
																	THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
													            				POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) 
														ELSE TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
																 	FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
														END
									END
				END
			WHEN w.Cust_Type = 'TP'  THEN 
				CASE  		
						 WHEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
								POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) IS NULL 
								OR 
						TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
								POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) = '' 
						THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
								FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) )
						ELSE TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
								POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) END
			END AS Last_Name ,
			CASE WHEN w.Cust_Type = 'AH'  THEN TO_CHAR(d.DT_OF_BIRTH , 'YYYY-MM-DD') ||  'T00:00:00'  WHEN w.Cust_Type = 'TP' THEN TO_CHAR(w.BIRTH_DATE  , 'YYYY-MM-DD') ||  'T00:00:00'  END as Birth_Date,
			CASE WHEN w.Cust_Type = 'AH'  THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(d.FTHR_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) 
						 WHEN w.Cust_Type = 'TP' THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w.FATHER_NAME , '[^A-Za-z ]', ' '), ' +', ' ')) END as Mother_Name,

			CASE WHEN w.Cust_Type = 'AH'  THEN D.IDNTFTN_TYPE_EDW_ID WHEN w.Cust_Type = 'TP' THEN 
						CASE WHEN LENGTH(REGEXP_REPLACE(w.w_cnic, '[^0-9]', '')) = 13 THEN 'NIC' 
									 WHEN REGEXP_SIMILAR( TRIM(REGEXP_REPLACE(w.w_cnic, '[^A-Za-z0-9]', '')), '^[A-Za-z0-9]+$') = 1 THEN 'PPT'  
									 ELSE CAST(NULL AS VARCHAR(10)) END
			END AS ssn_type,
			CASE WHEN w.Cust_Type = 'AH'  THEN d.IDNTFTN_VAL WHEN w.Cust_Type = 'TP' THEN w.w_cnic END as ssn,
			CASE WHEN w.Cust_Type = 'AH'  THEN d.CTRY_OF_NTLTY WHEN w.Cust_Type = 'TP' THEN 'PK' END as nationality1,
			'PK' as Residence,

			CASE WHEN w.Cust_Type = 'AH'  THEN case when d.MBL_NUM is not null AND d.MBL_NUM <> '' then 'PAPVT' when d.MBL_NUM is null OR d.MBL_NUM = '' then 'PAOFF' end
			WHEN w.Cust_Type = 'TP' THEN  'PAPVT' END as tph_contact_type,

			CASE WHEN w.Cust_Type = 'AH'  
			THEN case when d.MBL_NUM is not null AND d.MBL_NUM <> '' then 'COMOB' else 'COLAN' end
			WHEN w.Cust_Type = 'TP' THEN  'COMOB' END as tph_communication_type,

			'PK' as tph_country_prefix,
						
			CASE WHEN w.Cust_Type = 'AH'  THEN				  
			CASE
				when D.MBL_NUM is not null AND D.MBL_NUM <> ''  THEN REGEXP_REPLACE(REGEXP_REPLACE(TRIM(D.MBL_NUM), '[^0-9]', ''), '^(0092|[+]92|92|0)+', '')
		        when D.PHN_RSDNC is not null AND D.PHN_RSDNC <> '' then TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.PHN_RSDNC), '[^ ]+', 1, 1), '[^0-9]', '') )
		        else 
				case 
					WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' AND REGEXP_SIMILAR(D.PHN_BUSN, '.*[0-9].*') = '1' THEN CAST(NULL AS VARCHAR(11))
					WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' THEN CAST(NULL AS VARCHAR(11))
					ELSE 
						case
							when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,3) = '092' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3) 
							when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,2) = '92' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3)  
							ELSE trim(LEADING '0' FROM regexp_replace(D.PHN_BUSN, '[^0-9]', ''))
						end
				end 
			END		    
			WHEN w.Cust_Type = 'TP' THEN  TRIM(LEADING '0' FROM w.CONTACT_NO) END as tph_number,

			CASE WHEN w.Cust_Type = 'AH'  THEN	
			case when d.PERM_ADDR is not null and d.PERM_ADDR <> '' then 'PAPVT' 
						when d.PERM_ADDR is null or  d.PERM_ADDR = '' then 'PAOFF' end 
			WHEN w.Cust_Type = 'TP' THEN  'PAPVT' END as address_type,

			TRIM(OREPLACE(OREPLACE( 	
			CASE WHEN w.Cust_Type = 'AH'  THEN	
					CASE 
					WHEN TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is not null AND TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3
					              THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' ')  , '[[:space:]]+', ' '))  
					WHEN (TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
							       AND (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							      THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' ')) 
					WHEN (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
							       AND ( TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
								   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))
					WHEN (TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3 ) 
							       AND (TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
								   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))		   
					ELSE CAST(NULL AS VARCHAR(10)) 
					END
			WHEN w.Cust_Type = 'TP' THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(w.CUSTOMER_ADDRESS), '[^A-Za-z0-9 ]', ' ')  , '[[:space:]]+', ' ')) END ,CHR(13),' '),CHR(10), ' ')) as address,

			--CASE WHEN w.Cust_Type = 'AH'  THEN	CASE WHEN REGEXP_REPLACE(TRIM(d.RSDNTL_CITY), '[^A-Za-z ]', '') = '' THEN CAST(NULL AS VARCHAR(10)) ELSE REGEXP_REPLACE(TRIM(d.RSDNTL_CITY), '[^A-Za-z ]', '') END
			--WHEN w.Cust_Type = 'TP' THEN CAST(NULL	AS VARCHAR(10)) END as city,
			
			B.CITY_NAME AS city,

			'PK' as country_code,
			CASE WHEN w.Cust_Type = 'AH'  THEN
			case 
			when substr(d.IDNTFTN_VAL,1,1) IN ('1', '2') then 'KHYBER-PAKHTUNKHWA'
			when substr(d.IDNTFTN_VAL,1,1) IN ('3', '6') then 'PUNJAB'
			when substr(d.IDNTFTN_VAL,1,1) = '4' then 'SINDH'
			when substr(d.IDNTFTN_VAL,1,1) = '5' then 'BALOCHISTAN'
			when substr(d.IDNTFTN_VAL,1,1) = '7' then 'GILGIT-BALISTAN'
			when substr(d.IDNTFTN_VAL,1,1) = '8' then 'AZAD-KASHMIR'
			ELSE cast(null as varchar(10)) 
			end
			WHEN w.Cust_Type = 'TP' THEN  
			case 
			when substr(W.W_CNIC,1,1) IN ('1', '2') then 'KHYBER-PAKHTUNKHWA'
			when substr(W.W_CNIC,1,1) IN ('3', '6') then 'PUNJAB'
			when substr(W.W_CNIC,1,1) = '4' then 'SINDH'
			when substr(W.W_CNIC,1,1) = '5' then 'BALOCHISTAN'
			when substr(W.W_CNIC,1,1) = '7' then 'GILGIT-BALISTAN'
			when substr(W.W_CNIC,1,1) = '8' then 'AZAD-KASHMIR'
			ELSE cast(null as varchar(10)) 
			end
			END as state,

			CASE WHEN w.Cust_Type = 'AH'  THEN CASE WHEN O.OCPTN_DESC IS NOT NULL OR O.OCPTN_DESC <> '' THEN O.OCPTN_DESC ELSE 'Others' END
			WHEN w.Cust_Type = 'TP' THEN W.w_source_of_funds END AS occupation,
			'PK' as to_country,
			
			DENSE_RANK() OVER(PARTITION BY d.IDNTFTN_VAL ORDER BY d.START_DATE DESC) AS RN
			
			FROM TRXNS T
			INNER JOIN  dp_sdmt_dfdn.WALKIN_TXN W on T.tsactn_id = w.Transaction_ID 
			LEFT JOIN  DP_SDMVW_DFDN.DIM_CUST_VW d ON d.IDNTFTN_VAL = w.w_cnic and d.system_code = 'CBS'
			LEFT JOIN  DP_SDMT_DFDN.DIM_OCPTN_SS O ON O.OCPTN_EDW_ID = D.OCPTN_EDW_ID  and d.system_code = 'CBS'
			LEFT JOIN DP_SDMVW_DFDN.DIM_BRNCH_HIERARCHY_VW B ON T.BRNCH_SROGT_ID = B.BRNCH_SROGT_ID
			WHERE 1=1
			) X
		WHERE 1=1 
		AND X.RN = 1
		AND X.ssn_type NOT IN ('BFN', 'FXP')
		)

		
		, Final_Chunk AS (
		SELECT 
		T.CATEGORY,
		T.CATEGORY_TYPE_DESC,
		TRIM(T.TSACTN_ID) AS transactionnumber,
		B.BRNCH_DESC || ' (' || T.BRNCH_SROGT_ID || ')' AS transaction_location,
		CASE 
		WHEN CR_DR_IND = 'D' THEN 'CHEQUE WITHDRAWAL'  
		WHEN CR_DR_IND = 'C' THEN 'CASH DEPOSIT' 
		END AS transaction_description,
		TO_CHAR(T.TSACTN_DT , 'YYYY-MM-DD') ||  'T00:00:00' as date_transaction,
		B.BRNCH_DESC || ' (' || T.BRNCH_SROGT_ID || ')' AS teller,
		B.CITY_NAME AS authorized,
		'TMBRN' AS transmode_code,
		CASE WHEN T.CURY_EDW_ID = 'PKR' THEN CAST(T.TSACTN_AMT AS INT)
		ELSE CAST(T.FRGN_TSACTN_AMT_PKR AS INT) END AS amount_local,   
	
		CASE 
		WHEN CR_DR_IND = 'D' THEN 'FTCHQ'  
		WHEN CR_DR_IND = 'C' THEN 'FTCAS'
		END AS TFMC_from_funds_code,
		'UBL Bank Limited' AS TFMC_institution_name,
		'43' AS TFMC_institution_code,
		'FALSE' AS TFMC_non_bank_institution,
		BB.BRNCH_DESC || ' (' || T.ACCT_BRNCH_SROGT_ID || ')'  AS TFMC_branch,
		T.ACCT_SROGT_ID AS TFMC_account,
		T.ACCT_CURY_EDW_ID AS TFMC_currency_code,
		T.FRGN_CCY AS TFMC_Foreign_Currency_Code,
		T.FRGN_TSACTN_AMT AS TFMC_Foreign_Amount,
		T.EXCHANGE_RATE AS TFMC_Foreign_Exchange_Rate,
		T.ACCT_DESC AS TFMC_account_name,
		T.ACCT_TYPE_DESC AS TFMC_Acct_Type_Desc,
		T.ACCT_TYPE_CODE AS TFMC_personal_account_type,
		T.ACCT_DESC AS TFMC_name,
		T.CATEGORY_TYPE_CODE AS TFMC_incorporation_legal_form,
		T.CATEGORY_TYPE_DESC AS TFMC_Category_Type_Desc,
		OREPLACE(BUS.BUSINESS_DESC, '"', '') AS TFMC_business,

		case when d.MBL_NUM is not null and d.MBL_NUM <> '' then 'PAPVT' 
				  when d.MBL_NUM is null OR d.MBL_NUM = '' then 'PAOFF' end as TFMC_tph_contact_type,
		case when d.MBL_NUM is not null and d.MBL_NUM <> '' then 'COMOB' else 'COLAN' end as TFMC_tph_communication_type,
		'92' as TFMC_tph_country_prefix,			  
        CASE
			when D.MBL_NUM is not null AND D.MBL_NUM <> ''  
			THEN REGEXP_REPLACE(REGEXP_REPLACE(TRIM(D.MBL_NUM), '[^0-9]', ''), '^(0092|[+]92|92|0)+', '')
	        when D.PHN_RSDNC is not null AND D.PHN_RSDNC <> '' then TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.PHN_RSDNC), '[^ ]+', 1, 1), '[^0-9]', '') )
	        else 
			case 
				WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' AND REGEXP_SIMILAR(D.PHN_BUSN, '.*[0-9].*') = '1' THEN CAST(NULL AS VARCHAR(11))
				WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' THEN CAST(NULL AS VARCHAR(11))
				ELSE 
					case
						when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,3) = '092' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3) 
						when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,2) = '92' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3)  
						ELSE trim(LEADING '0' FROM regexp_replace(D.PHN_BUSN, '[^0-9]', ''))
					end
			end 
		END as TFMC_tph_number, 				  

		case when d.PERM_ADDR is not null and d.PERM_ADDR <> '' then 'PAPVT' 
					when d.PERM_ADDR is null OR d.PERM_ADDR = '' then 'PAOFF' end as TFMC_address_type,

	   	TRIM(OREPLACE(OREPLACE( 
		CASE 
		WHEN TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is not null AND TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3
		              THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' ')  , '[[:space:]]+', ' '))  
		WHEN (TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
				       AND (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
				      THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' ')) 
		WHEN (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
				       AND ( TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
					   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))
		WHEN (TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3 ) 
				       AND (TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
					   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))		   
		ELSE CAST(NULL AS VARCHAR(10)) 
		END
		,CHR(13),' '),CHR(10), ' ')) as TFMC_address,
		BB.CITY_NAME AS TFMC_city,
		'PK' as TFMC_country_code,
		CASE WHEN BB.PROV_NAME = 'FATA' THEN 'KHYBER-PAKHTUNKHWA'
					WHEN BB.PROV_NAME = 'ISLAMABAD' THEN 'PUNJAB'
					ELSE BB.PROV_NAME 
		END AS TFMC_State,
		'PK' AS TFMC_incorporation_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN 
					CASE 
					 WHEN d.GNDR IS NOT NULL THEN d.GNDR
					 WHEN d.GNDR IS NULL THEN 
								CASE WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'M' 
								WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'F' 
								ELSE CAST(NULL AS VARCHAR(10)) END END
			END
		) AS DIR1_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN 
					CASE 
					 WHEN d.TITL IS NOT NULL THEN d.TITL
					 WHEN d.TITL IS NULL THEN 
								CASE WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'MR' 
								WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'MS'
								ELSE CAST(NULL AS VARCHAR(10)) END END
			END
		) AS DIR1_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z0-9 ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
						FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
			END
		) AS DIR1_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN 
				CASE WHEN  REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0 
							THEN  TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
				              			  POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) )
							ELSE 
									CASE WHEN (D.FRST_NAME IS NULL AND D.MDL_NAME IS NULL AND D.LAST_NAME IS NULL) OR (D.FRST_NAME = '' AND D.MDL_NAME = '' AND D.LAST_NAME = '')
												THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
												 			FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
												ELSE 
														CASE WHEN REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0
																	THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
													            				POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) 
														ELSE TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
																 	FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
														END
									END
				END
			END
		) AS DIR1_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN TO_CHAR(D.DT_OF_BIRTH , 'YYYY-MM-DD') ||  'T00:00:00' 
			END
		) AS DIR1_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.FTHR_NAME, '[^A-Za-z ]', ' '), ' +', ' '))
			END
		) AS DIR1_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN D.IDNTFTN_TYPE_EDW_ID 
			END
		) AS DIR1_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN
							CASE WHEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) = '' THEN CAST(NULL AS VARCHAR(10)) 
											   ELSE TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) END
			END
		) AS DIR1_SSN

		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN D.CTRY_OF_NTLTY
			END
		) AS DIR1_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN 'PK'
			END
		) AS DIR1_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN
						  CASE WHEN D.MBL_NUM is not null AND D.MBL_NUM <> '' then 'PAPVT' when D.MBL_NUM is null OR D.MBL_NUM = '' then 'PAOFF' END
			END
		) AS DIR1_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN
						  CASE WHEN D.MBL_NUM is not null AND D.MBL_NUM <> '' then 'COMOB' else 'COLAN' END
			END
		) AS DIR1_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN '92'
			END
		) AS DIR1_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN 		
			
			CASE when D.MBL_NUM is not null AND D.MBL_NUM <> ''  
			THEN REGEXP_REPLACE(REGEXP_REPLACE(TRIM(D.MBL_NUM), '[^0-9]', ''), '^(0092|[+]92|92|0)+', '')
	        when D.PHN_RSDNC is not null AND D.PHN_RSDNC <> '' then TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.PHN_RSDNC), '[^ ]+', 1, 1), '[^0-9]', '') )
	        else case WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' AND REGEXP_SIMILAR(D.PHN_BUSN, '.*[0-9].*') = '1' THEN CAST(NULL AS VARCHAR(11)) WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' THEN CAST(NULL AS VARCHAR(11))
			ELSE case when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,3) = '092' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3) when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,2) = '92' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3)  
			ELSE trim(LEADING '0' FROM regexp_replace(D.PHN_BUSN, '[^0-9]', '')) end end END	
			END
		) AS DIR1_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN
						 CASE WHEN D.PERM_ADDR is not null and D.PERM_ADDR <> '' then 'PAPVT' 
									 WHEN D.PERM_ADDR is null OR D.PERM_ADDR = '' then 'PAOFF' END
			END
		) AS DIR1_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN 
				CASE 
				WHEN TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is not null AND TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3
				              THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' ')  , '[[:space:]]+', ' '))  
				WHEN (TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
						       AND (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
						      THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' ')) 
				WHEN (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
						       AND ( TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))
				WHEN (TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3 ) 
						       AND (TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))		   
				ELSE CAST(NULL AS VARCHAR(10)) 
				END
			END
		) AS DIR1_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CASE WHEN TRIM(D.RSDNTL_CITY) = '0' THEN CAST(NULL AS VARCHAR(10)) ELSE D.RSDNTL_CITY END
			END
		) AS DIR1_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN 'PK'
			END
		) AS DIR1_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN 
						 CASE  
							when substr(D.IDNTFTN_VAL,1,1) IN ('1', '2') then 'KHYBER-PAKHTUNKHWA'
							when substr(D.IDNTFTN_VAL,1,1) IN ('3', '6') then 'PUNJAB'
							when substr(D.IDNTFTN_VAL,1,1) = '4' then 'SINDH'
							when substr(D.IDNTFTN_VAL,1,1) = '5' then 'BALOCHISTAN'
							when substr(D.IDNTFTN_VAL,1,1) = '7' then 'GILGIT-BALISTAN'
							when substr(D.IDNTFTN_VAL,1,1) = '8' then 'AZAD-KASHMIR'
							ELSE cast(null as varchar(10)) 
						END 
			END
		) AS DIR1_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN  CASE WHEN _DO.OCPTN_DESC IS NOT NULL OR _DO.OCPTN_DESC <> '' THEN _DO.OCPTN_DESC ELSE 'Others' END 
			END
		) AS DIR1_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR1_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_FATHER_NAME

        , MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR2_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS DIR3_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR3_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR4_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR5_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_SSN

		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR6_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR7_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR8_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 9  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR9_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS DIR10_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 10  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR10_ROLE
		
		, CASE WHEN TRIM(LEADING '0' FROM REGEXP_REPLACE(D.TAX_NUM, '[^0-9]', '')) = '' THEN NULL 
		ELSE TRIM(LEADING '0' FROM REGEXP_REPLACE(D.TAX_NUM, '[^0-9]', '')) END AS TFMC_TAX_NUM
		
		, MAX('TRUE') AS SIGNATORY1_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 1  THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 1 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND  DD.D_RN IS NULL THEN 
						CASE 
							 WHEN d.GNDR IS NOT NULL THEN d.GNDR
							 WHEN d.GNDR IS NULL THEN 
										CASE WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'M' 
										WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'F' 
										ELSE CAST(NULL AS VARCHAR(10)) END END
			END
		) AS SIGNATORY1_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN 
					CASE 
					 WHEN d.TITL IS NOT NULL THEN d.TITL
					 WHEN d.TITL IS NULL THEN 
								CASE WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'MR' 
								WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'MS'
								ELSE CAST(NULL AS VARCHAR(10)) END END
			END
		) AS SIGNATORY1_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 1  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN  TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
						FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
			END
		) AS SIGNATORY1_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 1  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN 
					CASE WHEN  REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0 
								THEN  TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
					              			  POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) )
								ELSE 
										CASE WHEN (D.FRST_NAME IS NULL AND D.MDL_NAME IS NULL AND D.LAST_NAME IS NULL) OR (D.FRST_NAME = '' AND D.MDL_NAME = '' AND D.LAST_NAME = '')
													THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
													 			FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
													ELSE 
															CASE WHEN REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0
																		THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
														            				POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) 
															ELSE TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
																	 	FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
															END
										END
					END
			END
		) AS SIGNATORY1_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.FTHR_NAME, '[^A-Za-z ]', ' '), ' +', ' '))
			END
		) AS SIGNATORY1_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN D.IDNTFTN_TYPE_EDW_ID 
			END
		) AS SIGNATORY1_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN 
							CASE WHEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) = '' THEN CAST(NULL AS VARCHAR(10)) 
															   ELSE TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) END
			END
		) AS SIGNATORY1_SSN
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN D.CTRY_OF_NTLTY
			END
		) AS SIGNATORY1_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN 'PK'
			END
		) AS SIGNATORY1_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN 
						  CASE WHEN D.MBL_NUM is not null AND D.MBL_NUM <> '' then 'PAPVT' when D.MBL_NUM is null OR D.MBL_NUM = '' then 'PAOFF' END
			END
		) AS SIGNATORY1_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN 
						  CASE WHEN D.MBL_NUM is not null AND D.MBL_NUM <> '' then 'COMOB' else 'COLAN' END
			END
		) AS SIGNATORY1_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN '92'
			END
		) AS SIGNATORY1_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN 
			CASE when D.MBL_NUM is not null AND D.MBL_NUM <> ''  
			THEN REGEXP_REPLACE(REGEXP_REPLACE(TRIM(D.MBL_NUM), '[^0-9]', ''), '^(0092|[+]92|92|0)+', '')
	        when D.PHN_RSDNC is not null AND D.PHN_RSDNC <> '' then TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.PHN_RSDNC), '[^ ]+', 1, 1), '[^0-9]', '') )
	        else case WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' AND REGEXP_SIMILAR(D.PHN_BUSN, '.*[0-9].*') = '1' THEN CAST(NULL AS VARCHAR(11)) WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' THEN CAST(NULL AS VARCHAR(11))
			ELSE case when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,3) = '092' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3) when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,2) = '92' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3)  
			ELSE trim(LEADING '0' FROM regexp_replace(D.PHN_BUSN, '[^0-9]', '')) end end END	
			END
		) AS SIGNATORY1_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN TO_CHAR(D.DT_OF_BIRTH , 'YYYY-MM-DD') ||  'T00:00:00'
			END
		) AS SIGNATORY1_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CASE WHEN D.PERM_ADDR is not null and D.PERM_ADDR <> '' then 'PAPVT'  WHEN D.PERM_ADDR is null OR D.PERM_ADDR = '' then 'PAOFF' END
			END
		) AS SIGNATORY1_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN
			CASE 
				WHEN TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is not null AND TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3
				              THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' ')  , '[[:space:]]+', ' '))  
				WHEN (TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
						       AND (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
						      THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' ')) 
				WHEN (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
						       AND ( TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))
				WHEN (TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3 ) 
						       AND (TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))		   
				ELSE CAST(NULL AS VARCHAR(10)) 
				END
			END
		) AS SIGNATORY1_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CASE WHEN TRIM(D.RSDNTL_CITY) = '0' THEN CAST(NULL AS VARCHAR(10)) ELSE D.RSDNTL_CITY END
			END
		) AS SIGNATORY1_CITY
	
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN 'PK'
			END
		) AS SIGNATORY1_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN 
						  CASE  
							when substr(D.IDNTFTN_VAL,1,1) IN ('1', '2') then 'KHYBER-PAKHTUNKHWA'
							when substr(D.IDNTFTN_VAL,1,1) IN ('3', '6') then 'PUNJAB'
							when substr(D.IDNTFTN_VAL,1,1) = '4' then 'SINDH'
							when substr(D.IDNTFTN_VAL,1,1) = '5' then 'BALOCHISTAN'
							when substr(D.IDNTFTN_VAL,1,1) = '7' then 'GILGIT-BALISTAN'
							when substr(D.IDNTFTN_VAL,1,1) = '8' then 'AZAD-KASHMIR'
							ELSE cast(null as varchar(10)) 
						END
			END
		) AS SIGNATORY1_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CASE WHEN _DO.OCPTN_DESC IS NOT NULL OR _DO.OCPTN_DESC <> '' THEN _DO.OCPTN_DESC ELSE 'Others' END 
			END
		) AS SIGNATORY1_OCCUPATION
		
		, MAX(
			'ARPYS' 
		) AS SIGNATORY1_ROLE
		
		-----------------------------------------------------------------------------------------------------------------------------------------------------------
		, MAX('TRUE') AS SIGNATORY2_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 2 THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 2 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2 THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 2  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY2_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 2  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY2_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY2_SSN
		
		 , MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_CITY
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 2 THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_OCCUPATION
		
		, MAX(
			'ARPYS'
		) AS SIGNATORY2_ROLE
		 
		, MAX('TRUE') AS SIGNATORY3_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 3 THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 3 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3 THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 3  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY3_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 3  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY3_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY3_SSN
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_CITY
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 3 THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_OCCUPATION
		
		, MAX(
			'ARPYS'
		) AS SIGNATORY3_ROLE
		
		, MAX('TRUE') AS SIGNATORY4_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 4 THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 4 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4 THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 4  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY4_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 4  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY4_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY4_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY4_SSN
		
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_CITY
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 4 THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_OCCUPATION
		
		, MAX(
			'ARPYS'
		) AS SIGNATORY4_ROLE
		
		, MAX('TRUE') AS SIGNATORY5_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 5 THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 5 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5 THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 5  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY5_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 5  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY5_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY5_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY5_SSN
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_CITY
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 5 THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_OCCUPATION
		
		, MAX(
			'ARPYS'
		) AS SIGNATORY5_ROLE
		
		, MAX('TRUE') AS SIGNATORY6_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 6 THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 6 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6 THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 6  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY6_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 6  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY6_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY6_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY6_SSN
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_CITY
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 6 THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_OCCUPATION
		
		, MAX(
			'ARPYS'
		) AS SIGNATORY6_ROLE
		
		, MAX('TRUE') AS SIGNATORY7_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 7 THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 7 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7 THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 7  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY7_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 7  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY7_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY7_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY7_SSN
		
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_CITY
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 7 THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_OCCUPATION
		
		, MAX(
			'ARPYS'
		) AS SIGNATORY7_ROLE
		
		, MAX('TRUE') AS SIGNATORY8_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 8 THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 8 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8 THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 8  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY8_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 8  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY8_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY8_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY8_SSN
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_CITY
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 8 THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_OCCUPATION
		
		, MAX(
			'ARPYS'
		) AS SIGNATORY8_ROLE
		
		, TO_CHAR(T.ACCT_ORIGNL_OPN_DT , 'YYYY-MM-DD') ||  'T00:00:00' AS TFMC_open,
		'ASACT' as TFMC_status_code,
		-- d.CTRY_OF_NTLTY as TFMC_to_country
		'PK' AS TFMC_from_country,
		
		CASE 
		WHEN CR_DR_IND = 'D' THEN 'FTCAS'
		WHEN CR_DR_IND = 'C' THEN 'FTDEP' 
		END AS TTMC_to_funds_code,
		W.Gender AS TTMC_Gender,
		W."Title" AS TTMC_Title,
		W.First_Name AS TTMC_First_Name,
		W.Last_Name AS TTMC_Last_Name,
		W.Birth_Date AS TTMC_Birth_Date,
		W.Mother_Name AS TTMC_Mother_Name,
		W.ssn_type AS TTMC_ssn_type,
		W.ssn AS TTMC_ssn,
		W.nationality1 AS TTMC_nationality1,
		W.Residence AS TTMC_Residence,
		W.tph_contact_type AS TTMC_tph_contact_type,
		W.tph_communication_type AS TTMC_tph_communication_type,
		W.tph_country_prefix AS TTMC_tph_country_prefix,
		W.tph_number AS TTMC_tph_number,
		W.address_type AS TTMC_address_type,
		W.address AS TTMC_address,
		W.city AS TTMC_city,
		W.country_code AS TTMC_country_code,
		W.state AS TTMC_state,
		W.occupation AS TTMC_occupation,
		W.to_country AS TTMC_to_country

		FROM TRXNS T
		LEFT JOIN DP_SDMVW_DFDN.DIM_CUST_VW d ON d.CUST_SROGT_ID = T.CUST_SROGT_ID and d.system_code = 'CBS'
		LEFT JOIN DP_SDMT_DFDN.DIM_OCPTN_SS _DO ON D.OCPTN_EDW_ID = _DO.OCPTN_EDW_ID
		LEFT JOIN DP_WRK_CBS.FM_CLIENT_DAILY fmd ON fmd.client_no = T.CUST_SROGT_ID
		LEFT JOIN DP_SDMVW_DFDN.DIM_BUSINESS_VW BUS ON fmd.business = bus.BUSINESS
		LEFT JOIN DP_SDMVW_DFDN.DIM_CUST_TYPE_VW CTY ON D.CUST_TYPE_EDW_ID = CTY.CUST_TYPE_EDW_ID
		LEFT JOIN DP_SDMVW_DFDN.DIM_BRNCH_HIERARCHY_VW B ON T.BRNCH_SROGT_ID = B.BRNCH_SROGT_ID
		LEFT JOIN DP_SDMVW_DFDN.DIM_BRNCH_HIERARCHY_VW BB ON T.ACCT_BRNCH_SROGT_ID = BB.BRNCH_SROGT_ID 
		LEFT JOIN MANDATE M ON M.ACCT_SROGT_ID = T.ACCT_SROGT_ID
		LEFT JOIN DIRECTORS DD ON DD.CUST_SROGT_ID = T.CUST_SROGT_ID 
		LEFT JOIN WALKIN_DETAILS W ON W.Transaction_ID = T.TSACTN_ID
		WHERE 1=1 
		GROUP BY 
		CATEGORY,CATEGORY_TYPE_DESC,transactionnumber,transaction_location,transaction_description,date_transaction,teller,authorized,transmode_code,amount_local,
		TFMC_from_funds_code,TFMC_institution_name,TFMC_institution_code,TFMC_non_bank_institution,TFMC_branch,TFMC_account,TFMC_currency_code,
		TFMC_Foreign_Currency_Code, TFMC_Foreign_Amount, TFMC_Foreign_Exchange_Rate, TFMC_account_name,TFMC_Acct_Type_Desc,TFMC_personal_account_type,TFMC_name,TFMC_incorporation_legal_form, TFMC_Category_Type_Desc,
		TFMC_business,TFMC_tph_contact_type,TFMC_tph_communication_type, TFMC_tph_country_prefix,TFMC_tph_number,TFMC_address_type,TFMC_address,TFMC_city,TFMC_country_code,
		TFMC_state,TFMC_incorporation_country_code,TFMC_TAX_NUM, TFMC_open,TFMC_status_code,TFMC_from_country ,
		
		TTMC_to_funds_code,TTMC_Gender,TTMC_Title,TTMC_First_Name,TTMC_Last_Name,TTMC_Birth_Date,TTMC_Mother_Name,TTMC_ssn_type,TTMC_ssn,TTMC_nationality1,TTMC_Residence,
		TTMC_tph_contact_type,TTMC_tph_communication_type,TTMC_tph_country_prefix,TTMC_tph_number,TTMC_address_type,TTMC_address,TTMC_city,TTMC_country_code,TTMC_state,TTMC_occupation,TTMC_to_country
		)
		
		, DATA_V1 AS (
		
		SELECT 
		CAST(CATEGORY AS VARCHAR(20)) AS CATEGORY , 
	    CAST(CATEGORY_TYPE_DESC AS VARCHAR(99)) AS CATEGORY_TYPE_DESC ,
		CAST(transactionnumber AS BIGINT) AS transactionnumber,
		CAST(transaction_location AS VARCHAR(99)) AS transaction_location,
		CAST(transaction_description AS VARCHAR(99)) AS transaction_description,
		CAST(date_transaction AS VARCHAR(20)) AS date_transaction,
		CAST(teller AS VARCHAR(99)) AS teller ,
		CAST(authorized AS VARCHAR(99)) AS authorized,
		CAST(transmode_code AS VARCHAR(10)) AS transmode_code,
		CAST(amount_local AS INT) AS amount_local,
		--------------------------------------- FROM MY CLEINT TAG -----------------------------------------------------------
		CAST(TFMC_from_funds_code AS VARCHAR(20)) AS TFMC_from_funds_code,
		CAST(TFMC_institution_name AS VARCHAR(99)) AS TFMC_institution_name,
		CAST(TFMC_institution_code AS VARCHAR(99)) AS TFMC_institution_code,
		CAST(TFMC_non_bank_institution AS VARCHAR(99)) AS TFMC_non_bank_institution,
		CAST(TFMC_branch AS VARCHAR(99)) AS TFMC_branch,
		CAST(TFMC_account AS VARCHAR(20)) AS TFMC_account,
		CAST(TFMC_currency_code AS VARCHAR(10)) AS TFMC_currency_code,
		CAST(TFMC_Foreign_Currency_Code AS VARCHAR(10)) AS TFMC_Foreign_Currency_Code,
		CAST(TFMC_Foreign_Amount AS INT) AS TFMC_Foreign_Amount  ,
		CAST(TFMC_Foreign_Exchange_Rate AS DECIMAL(38,4)) AS TFMC_Foreign_Exchange_Rate,
		CAST(TFMC_account_name AS VARCHAR(99)) AS TFMC_account_name, 
		CAST(TFMC_personal_account_type AS VARCHAR(20)) AS TFMC_personal_account_type, 
		CAST(TFMC_name AS VARCHAR(99)) AS TFMC_name, 
		CAST(TFMC_incorporation_legal_form AS VARCHAR(20)) AS TFMC_incorporation_legal_form, 
		CAST(TFMC_business AS VARCHAR(99)) AS TFMC_business, 
		CAST(TFMC_tph_contact_type AS VARCHAR(20)) AS TFMC_tph_contact_type, 
		CAST(TFMC_tph_communication_type AS VARCHAR(20)) AS TFMC_tph_communication_type, 
		CAST(TFMC_tph_country_prefix AS VARCHAR(10)) AS TFMC_tph_country_prefix ,
		CAST(CASE WHEN TFMC_tph_number IS NULL OR TFMC_tph_number = '' THEN COALESCE(SIGNATORY1_TPH_NUMBER, DIR1_TPH_NUMBER) ELSE TFMC_tph_number END AS VARCHAR(20)) AS TFMC_tph_number,
		CAST(TFMC_address_type AS VARCHAR(10)) AS TFMC_address_type,
		CAST(CASE WHEN TFMC_address IS NULL OR TFMC_address = '' THEN COALESCE(SIGNATORY1_ADDRESS, DIR1_ADDRESS) ELSE TFMC_address END AS VARCHAR(99)) AS TFMC_address,
		CAST(TFMC_city AS VARCHAR(50)) AS TFMC_city,
		CAST(TFMC_country_code AS VARCHAR(10)) AS TFMC_country_code,
		CAST(TFMC_state AS VARCHAR(50)) AS TFMC_state,
		CAST(TFMC_incorporation_country_code AS VARCHAR(20)) AS TFMC_incorporation_country_code,
		------------------------------------- DIRECTOR 1 -----------------------------------------
		CAST(DIR1_GNDR AS VARCHAR(10)) AS DIR1_GNDR,
		CAST(DIR1_TITL AS VARCHAR(10)) AS DIR1_TITL,
		CAST(DIR1_FIRSTNAME AS VARCHAR(99)) AS DIR1_FIRSTNAME,
		CAST(DIR1_LASTNAME AS VARCHAR(99)) AS DIR1_LASTNAME,
		CAST(DIR1_FATHER_NAME AS VARCHAR(99)) AS DIR1_FATHER_NAME,
		CAST(DIR1_SSN_TYPE AS VARCHAR(10)) AS DIR1_SSN_TYPE,
		CAST(CASE WHEN DIR1_SSN_TYPE IN ('NIC', 'PPT','POC') THEN DIR1_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR1_SSN,
	    CAST(DIR1_nationality1 AS VARCHAR(10)) AS DIR1_nationality1,
	    CAST(DIR1_Residence AS VARCHAR(10)) AS DIR1_Residence,
	    CAST(DIR1_tph_contact_type AS VARCHAR(10)) AS DIR1_tph_contact_type,
	    CAST(DIR1_tph_communication_type AS VARCHAR(10)) AS DIR1_tph_communication_type,
	    CAST(DIR1_tph_country_prefix AS VARCHAR(10)) AS DIR1_tph_country_prefix,
		CAST(CASE WHEN DIR1_TPH_NUMBER IS NULL OR DIR1_TPH_NUMBER = '' THEN 
					COALESCE(CASE WHEN SIGNATORY1_TPH_NUMBER IS NULL OR SIGNATORY1_TPH_NUMBER = '' THEN TTMC_tph_number END, SIGNATORY1_TPH_NUMBER ) ELSE DIR1_TPH_NUMBER END AS VARCHAR(50)) AS DIR1_TPH_NUMBER,
		CAST(CASE WHEN DIR1_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR1_DATE_OF_BIRTH, 3) ELSE DIR1_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR1_DATE_OF_BIRTH,
	    CAST(DIR1_address_type AS VARCHAR(10)) AS DIR1_address_type,
		CAST(DIR1_ADDRESS AS VARCHAR(99)) AS DIR1_ADDRESS,
	    CAST(DIR1_CITY AS VARCHAR(20)) AS DIR1_CITY,
	    CAST(DIR1_country_code AS VARCHAR(10)) AS DIR1_country_code,
	    CAST(DIR1_STATE AS VARCHAR(20)) AS DIR1_STATE,
		CAST(DIR1_OCCUPATION AS VARCHAR(99)) AS DIR1_OCCUPATION,
	    CAST(DIR1_ROLE AS VARCHAR(10)) AS DIR1_ROLE,
		------------------------------------- DIRECTOR 2 -----------------------------------------
		CAST(DIR2_GNDR AS VARCHAR(10)) AS DIR2_GNDR,
		CAST(DIR2_TITL AS VARCHAR(10)) AS DIR2_TITL,
		CAST(DIR2_FIRSTNAME AS VARCHAR(99)) AS DIR2_FIRSTNAME,
		CAST(DIR2_LASTNAME AS VARCHAR(99)) AS DIR2_LASTNAME,
		CAST(DIR2_FATHER_NAME AS VARCHAR(99)) AS DIR2_FATHER_NAME,
		CAST(DIR2_SSN_TYPE AS VARCHAR(10)) AS DIR2_SSN_TYPE,
		CAST(CASE WHEN DIR2_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR2_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR2_SSN,
	    CAST(DIR2_nationality1 AS VARCHAR(10)) AS DIR2_nationality1,
	    CAST(DIR2_Residence AS VARCHAR(10)) AS DIR2_Residence,
	    CAST(DIR2_tph_contact_type AS VARCHAR(10)) AS DIR2_tph_contact_type,
	    CAST(DIR2_tph_communication_type AS VARCHAR(10)) AS DIR2_tph_communication_type,
	    CAST(DIR2_tph_country_prefix AS VARCHAR(10)) AS DIR2_tph_country_prefix,
		CAST(DIR2_TPH_NUMBER AS VARCHAR(20)) AS DIR2_TPH_NUMBER,
		CAST(CASE WHEN DIR2_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR2_DATE_OF_BIRTH, 3) ELSE DIR2_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR2_DATE_OF_BIRTH,
	    CAST(DIR2_address_type AS VARCHAR(10)) AS DIR2_address_type,
		CAST(DIR2_ADDRESS AS VARCHAR(99)) AS DIR2_ADDRESS,
	    CAST(DIR2_CITY AS VARCHAR(20)) AS DIR2_CITY,
	    CAST(DIR2_country_code AS VARCHAR(10)) AS DIR2_country_code,
	    CAST(DIR2_STATE AS VARCHAR(20)) AS DIR2_STATE,
		CAST(DIR2_OCCUPATION AS VARCHAR(99)) AS DIR2_OCCUPATION,
	    CAST(CASE WHEN DIR2_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR2_ROLE END AS VARCHAR(10)) AS DIR2_ROLE,
		------------------------------------- DIRECTOR 3 -----------------------------------------
		CAST(DIR3_GNDR AS VARCHAR(10)) AS DIR3_GNDR,
		CAST(DIR3_TITL AS VARCHAR(10)) AS DIR3_TITL,
		CAST(DIR3_FIRSTNAME AS VARCHAR(99)) AS DIR3_FIRSTNAME,
		CAST(DIR3_LASTNAME AS VARCHAR(99)) AS DIR3_LASTNAME,
		CAST(DIR3_FATHER_NAME AS VARCHAR(99)) AS DIR3_FATHER_NAME,
		CAST(DIR3_SSN_TYPE AS VARCHAR(10)) AS DIR3_SSN_TYPE,
		CAST(CASE WHEN DIR3_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR3_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR3_SSN,
	    CAST(DIR3_nationality1 AS VARCHAR(10)) AS DIR3_nationality1,
	    CAST(DIR3_Residence AS VARCHAR(10)) AS DIR3_Residence,
	    CAST(DIR3_tph_contact_type AS VARCHAR(10)) AS DIR3_tph_contact_type,
	    CAST(DIR3_tph_communication_type AS VARCHAR(10)) AS DIR3_tph_communication_type,
	    CAST(DIR3_tph_country_prefix AS VARCHAR(10)) AS DIR3_tph_country_prefix,
		CAST(DIR3_TPH_NUMBER AS VARCHAR(20)) AS DIR3_TPH_NUMBER,
		CAST(CASE WHEN DIR3_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR3_DATE_OF_BIRTH, 3) ELSE DIR3_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR3_DATE_OF_BIRTH,
	    CAST(DIR3_address_type AS VARCHAR(10)) AS DIR3_address_type,
		CAST(DIR3_ADDRESS AS VARCHAR(99)) AS DIR3_ADDRESS,
	    CAST(DIR3_CITY AS VARCHAR(20)) AS DIR3_CITY,
	    CAST(DIR3_country_code AS VARCHAR(10)) AS DIR3_country_code,
	    CAST(DIR3_STATE AS VARCHAR(20)) AS DIR3_STATE,
		CAST(DIR3_OCCUPATION AS VARCHAR(99)) AS DIR3_OCCUPATION,
	    CAST(CASE WHEN DIR3_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR3_ROLE END AS VARCHAR(10)) AS DIR3_ROLE,
		------------------------------------- DIRECTOR 4 -----------------------------------------
		CAST(DIR4_GNDR AS VARCHAR(10)) AS DIR4_GNDR,
		CAST(DIR4_TITL AS VARCHAR(10)) AS DIR4_TITL,
		CAST(DIR4_FIRSTNAME AS VARCHAR(99)) AS DIR4_FIRSTNAME,
		CAST(DIR4_LASTNAME AS VARCHAR(99)) AS DIR4_LASTNAME,
		CAST(DIR4_FATHER_NAME AS VARCHAR(99)) AS DIR4_FATHER_NAME,
		CAST(DIR4_SSN_TYPE AS VARCHAR(10)) AS DIR4_SSN_TYPE,
		CAST(CASE WHEN DIR4_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR4_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR4_SSN,
	    CAST(DIR4_nationality1 AS VARCHAR(10)) AS DIR4_nationality1,
	    CAST(DIR4_Residence AS VARCHAR(10)) AS DIR4_Residence,
	    CAST(DIR4_tph_contact_type AS VARCHAR(10)) AS DIR4_tph_contact_type,
	    CAST(DIR4_tph_communication_type AS VARCHAR(10)) AS DIR4_tph_communication_type,
	    CAST(DIR4_tph_country_prefix AS VARCHAR(10)) AS DIR4_tph_country_prefix,
		CAST(DIR4_TPH_NUMBER AS VARCHAR(20)) AS DIR4_TPH_NUMBER,
		CAST(CASE WHEN DIR4_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR4_DATE_OF_BIRTH, 3) ELSE DIR4_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR4_DATE_OF_BIRTH,
	    CAST(DIR4_address_type AS VARCHAR(10)) AS DIR4_address_type,
		CAST(DIR4_ADDRESS AS VARCHAR(99)) AS DIR4_ADDRESS,
	    CAST(DIR4_CITY AS VARCHAR(20)) AS DIR4_CITY,
	    CAST(DIR4_country_code AS VARCHAR(10)) AS DIR4_country_code,
	    CAST(DIR4_STATE AS VARCHAR(20)) AS DIR4_STATE,
		CAST(DIR4_OCCUPATION AS VARCHAR(99)) AS DIR4_OCCUPATION,
	    CAST(CASE WHEN DIR4_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR4_ROLE END AS VARCHAR(10)) AS DIR4_ROLE,
		------------------------------------- DIRECTOR 5 -----------------------------------------
		CAST(DIR5_GNDR AS VARCHAR(10)) AS DIR5_GNDR,
		CAST(DIR5_TITL AS VARCHAR(10)) AS DIR5_TITL,
		CAST(DIR5_FIRSTNAME AS VARCHAR(99)) AS DIR5_FIRSTNAME,
		CAST(DIR5_LASTNAME AS VARCHAR(99)) AS DIR5_LASTNAME,
		CAST(DIR5_FATHER_NAME AS VARCHAR(99)) AS DIR5_FATHER_NAME,
		CAST(DIR5_SSN_TYPE AS VARCHAR(10)) AS DIR5_SSN_TYPE,
		CAST(CASE WHEN DIR5_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR5_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR5_SSN,
	    CAST(DIR5_nationality1 AS VARCHAR(10)) AS DIR5_nationality1,
	    CAST(DIR5_Residence AS VARCHAR(10)) AS DIR5_Residence,
	    CAST(DIR5_tph_contact_type AS VARCHAR(10)) AS DIR5_tph_contact_type,
	    CAST(DIR5_tph_communication_type AS VARCHAR(10)) AS DIR5_tph_communication_type,
	    CAST(DIR5_tph_country_prefix AS VARCHAR(10)) AS DIR5_tph_country_prefix,
		CAST(DIR5_TPH_NUMBER AS VARCHAR(20)) AS DIR5_TPH_NUMBER,
		CAST(CASE WHEN DIR5_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR5_DATE_OF_BIRTH, 3) ELSE DIR5_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR5_DATE_OF_BIRTH,
	    CAST(DIR5_address_type AS VARCHAR(10)) AS DIR5_address_type,
		CAST(DIR5_ADDRESS AS VARCHAR(99)) AS DIR5_ADDRESS,
	    CAST(DIR5_CITY AS VARCHAR(20)) AS DIR5_CITY,
	    CAST(DIR5_country_code AS VARCHAR(10)) AS DIR5_country_code,
	    CAST(DIR5_STATE AS VARCHAR(20)) AS DIR5_STATE,
		CAST(DIR5_OCCUPATION AS VARCHAR(99)) AS DIR5_OCCUPATION,
	    CAST(CASE WHEN DIR5_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR5_ROLE END AS VARCHAR(10)) AS DIR5_ROLE,
		------------------------------------- DIRECTOR 6 -----------------------------------------
		CAST(DIR6_GNDR AS VARCHAR(10)) AS DIR6_GNDR,
		CAST(DIR6_TITL AS VARCHAR(10)) AS DIR6_TITL,
		CAST(DIR6_FIRSTNAME AS VARCHAR(99)) AS DIR6_FIRSTNAME,
		CAST(DIR6_LASTNAME AS VARCHAR(99)) AS DIR6_LASTNAME,
		CAST(DIR6_FATHER_NAME AS VARCHAR(99)) AS DIR6_FATHER_NAME,
		CAST(DIR6_SSN_TYPE AS VARCHAR(10)) AS DIR6_SSN_TYPE,
		CAST(CASE WHEN DIR6_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR6_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR6_SSN,
	    CAST(DIR6_nationality1 AS VARCHAR(10)) AS DIR6_nationality1,
	    CAST(DIR6_Residence AS VARCHAR(10)) AS DIR6_Residence,
	    CAST(DIR6_tph_contact_type AS VARCHAR(10)) AS DIR6_tph_contact_type,
	    CAST(DIR6_tph_communication_type AS VARCHAR(10)) AS DIR6_tph_communication_type,
	    CAST(DIR6_tph_country_prefix AS VARCHAR(10)) AS DIR6_tph_country_prefix,
		CAST(DIR6_TPH_NUMBER AS VARCHAR(20)) AS DIR6_TPH_NUMBER,
		CAST(CASE WHEN DIR6_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR6_DATE_OF_BIRTH, 3) ELSE DIR6_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR6_DATE_OF_BIRTH,
	    CAST(DIR6_address_type AS VARCHAR(10)) AS DIR6_address_type,
		CAST(DIR6_ADDRESS AS VARCHAR(99)) AS DIR6_ADDRESS,
	    CAST(DIR6_CITY AS VARCHAR(20)) AS DIR6_CITY,
	    CAST(DIR6_country_code AS VARCHAR(10)) AS DIR6_country_code,
	    CAST(DIR6_STATE AS VARCHAR(20)) AS DIR6_STATE,
		CAST(DIR6_OCCUPATION AS VARCHAR(99)) AS DIR6_OCCUPATION,
	    CAST(CASE WHEN DIR6_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR6_ROLE END AS VARCHAR(10)) AS DIR6_ROLE,
		------------------------------------- DIRECTOR 7 -----------------------------------------
		CAST(DIR7_GNDR AS VARCHAR(10)) AS DIR7_GNDR,
		CAST(DIR7_TITL AS VARCHAR(10)) AS DIR7_TITL,
		CAST(DIR7_FIRSTNAME AS VARCHAR(99)) AS DIR7_FIRSTNAME,
		CAST(DIR7_LASTNAME AS VARCHAR(99)) AS DIR7_LASTNAME,
		CAST(DIR7_FATHER_NAME AS VARCHAR(99)) AS DIR7_FATHER_NAME,
		CAST(DIR7_SSN_TYPE AS VARCHAR(10)) AS DIR7_SSN_TYPE,
		CAST(CASE WHEN DIR7_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR7_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR7_SSN,
	    CAST(DIR7_nationality1 AS VARCHAR(10)) AS DIR7_nationality1,
	    CAST(DIR7_Residence AS VARCHAR(10)) AS DIR7_Residence,
	    CAST(DIR7_tph_contact_type AS VARCHAR(10)) AS DIR7_tph_contact_type,
	    CAST(DIR7_tph_communication_type AS VARCHAR(10)) AS DIR7_tph_communication_type,
	    CAST(DIR7_tph_country_prefix AS VARCHAR(10)) AS DIR7_tph_country_prefix,
		CAST(DIR7_TPH_NUMBER AS VARCHAR(20)) AS DIR7_TPH_NUMBER,
		CAST(CASE WHEN DIR7_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR7_DATE_OF_BIRTH, 3) ELSE DIR7_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR7_DATE_OF_BIRTH,
	    CAST(DIR7_address_type AS VARCHAR(10)) AS DIR7_address_type,
		CAST(DIR7_ADDRESS AS VARCHAR(99)) AS DIR7_ADDRESS,
	    CAST(DIR7_CITY AS VARCHAR(20)) AS DIR7_CITY,
	    CAST(DIR7_country_code AS VARCHAR(10)) AS DIR7_country_code,
	    CAST(DIR7_STATE AS VARCHAR(20)) AS DIR7_STATE,
		CAST(DIR7_OCCUPATION AS VARCHAR(99)) AS DIR7_OCCUPATION,
	    CAST(CASE WHEN DIR7_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR7_ROLE END AS VARCHAR(10)) AS DIR7_ROLE,
		------------------------------------- DIRECTOR 8 -----------------------------------------
		CAST(DIR8_GNDR AS VARCHAR(10)) AS DIR8_GNDR,
		CAST(DIR8_TITL AS VARCHAR(10)) AS DIR8_TITL,
		CAST(DIR8_FIRSTNAME AS VARCHAR(99)) AS DIR8_FIRSTNAME,
		CAST(DIR8_LASTNAME AS VARCHAR(99)) AS DIR8_LASTNAME,
		CAST(DIR8_FATHER_NAME AS VARCHAR(99)) AS DIR8_FATHER_NAME,
		CAST(DIR8_SSN_TYPE AS VARCHAR(10)) AS DIR8_SSN_TYPE,
		CAST(CASE WHEN DIR8_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR8_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR8_SSN,
	    CAST(DIR8_nationality1 AS VARCHAR(10)) AS DIR8_nationality1,
	    CAST(DIR8_Residence AS VARCHAR(10)) AS DIR8_Residence,
	    CAST(DIR8_tph_contact_type AS VARCHAR(10)) AS DIR8_tph_contact_type,
	    CAST(DIR8_tph_communication_type AS VARCHAR(10)) AS DIR8_tph_communication_type,
	    CAST(DIR8_tph_country_prefix AS VARCHAR(10)) AS DIR8_tph_country_prefix,
		CAST(DIR8_TPH_NUMBER AS VARCHAR(20)) AS DIR8_TPH_NUMBER,
		CAST(CASE WHEN DIR8_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR8_DATE_OF_BIRTH, 3) ELSE DIR8_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR8_DATE_OF_BIRTH,
	    CAST(DIR8_address_type AS VARCHAR(10)) AS DIR8_address_type,
		CAST(DIR8_ADDRESS AS VARCHAR(99)) AS DIR8_ADDRESS,
	    CAST(DIR8_CITY AS VARCHAR(20)) AS DIR8_CITY,
	    CAST(DIR8_country_code AS VARCHAR(10)) AS DIR8_country_code,
	    CAST(DIR8_STATE AS VARCHAR(20)) AS DIR8_STATE,
		CAST(DIR8_OCCUPATION AS VARCHAR(99)) AS DIR8_OCCUPATION,
	    CAST(CASE WHEN DIR8_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR8_ROLE END AS VARCHAR(10)) AS DIR8_ROLE,
		------------------------------------- DIRECTOR 9 -----------------------------------------
		CAST(DIR9_GNDR AS VARCHAR(10)) AS DIR9_GNDR,
		CAST(DIR9_TITL AS VARCHAR(10)) AS DIR9_TITL,
		CAST(DIR9_FIRSTNAME AS VARCHAR(99)) AS DIR9_FIRSTNAME,
		CAST(DIR9_LASTNAME AS VARCHAR(99)) AS DIR9_LASTNAME,
		CAST(DIR9_FATHER_NAME AS VARCHAR(99)) AS DIR9_FATHER_NAME,
		CAST(DIR9_SSN_TYPE AS VARCHAR(10)) AS DIR9_SSN_TYPE,
		CAST(CASE WHEN DIR9_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR9_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR9_SSN,
	    CAST(DIR9_nationality1 AS VARCHAR(10)) AS DIR9_nationality1,
	    CAST(DIR9_Residence AS VARCHAR(10)) AS DIR9_Residence,
	    CAST(DIR9_tph_contact_type AS VARCHAR(10)) AS DIR9_tph_contact_type,
	    CAST(DIR9_tph_communication_type AS VARCHAR(10)) AS DIR9_tph_communication_type,
	    CAST(DIR9_tph_country_prefix AS VARCHAR(10)) AS DIR9_tph_country_prefix,
		CAST(DIR9_TPH_NUMBER AS VARCHAR(20)) AS DIR9_TPH_NUMBER,
		CAST(CASE WHEN DIR9_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR9_DATE_OF_BIRTH, 3) ELSE DIR9_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR9_DATE_OF_BIRTH,
	    CAST(DIR9_address_type AS VARCHAR(10)) AS DIR9_address_type,
		CAST(DIR9_ADDRESS AS VARCHAR(99)) AS DIR9_ADDRESS,
	    CAST(DIR9_CITY AS VARCHAR(20)) AS DIR9_CITY,
	    CAST(DIR9_country_code AS VARCHAR(10)) AS DIR9_country_code,
	    CAST(DIR9_STATE AS VARCHAR(20)) AS DIR9_STATE,
		CAST(DIR9_OCCUPATION AS VARCHAR(99)) AS DIR9_OCCUPATION,
	    CAST(CASE WHEN DIR9_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR9_ROLE END AS VARCHAR(10)) AS DIR9_ROLE,
		------------------------------------- DIRECTOR 10 -----------------------------------------
		CAST(DIR10_GNDR AS VARCHAR(10)) AS DIR10_GNDR,
		CAST(DIR10_TITL AS VARCHAR(10)) AS DIR10_TITL,
		CAST(DIR10_FIRSTNAME AS VARCHAR(99)) AS DIR10_FIRSTNAME,
		CAST(DIR10_LASTNAME AS VARCHAR(99)) AS DIR10_LASTNAME,
		CAST(DIR10_FATHER_NAME AS VARCHAR(99)) AS DIR10_FATHER_NAME,
		CAST(DIR10_SSN_TYPE AS VARCHAR(10)) AS DIR10_SSN_TYPE,
		CAST(CASE WHEN DIR10_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR10_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR10_SSN,
	    CAST(DIR10_nationality1 AS VARCHAR(10)) AS DIR10_nationality1,
	    CAST(DIR10_Residence AS VARCHAR(10)) AS DIR10_Residence,
	    CAST(DIR10_tph_contact_type AS VARCHAR(10)) AS DIR10_tph_contact_type,
	    CAST(DIR10_tph_communication_type AS VARCHAR(10)) AS DIR10_tph_communication_type,
	    CAST(DIR10_tph_country_prefix AS VARCHAR(10)) AS DIR10_tph_country_prefix,
		CAST(DIR10_TPH_NUMBER AS VARCHAR(20)) AS DIR10_TPH_NUMBER,
		CAST(CASE WHEN DIR10_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR10_DATE_OF_BIRTH, 3) ELSE DIR10_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR10_DATE_OF_BIRTH,
	    CAST(DIR10_address_type AS VARCHAR(10)) AS DIR10_address_type,
		CAST(DIR10_ADDRESS AS VARCHAR(99)) AS DIR10_ADDRESS,
	    CAST(DIR10_CITY AS VARCHAR(20)) AS DIR10_CITY,
	    CAST(DIR10_country_code AS VARCHAR(10)) AS DIR10_country_code,
	    CAST(DIR10_STATE AS VARCHAR(20)) AS DIR10_STATE,
		CAST(DIR10_OCCUPATION AS VARCHAR(99)) AS DIR10_OCCUPATION,
	    CAST(CASE WHEN DIR10_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR10_ROLE END AS VARCHAR(10)) AS DIR10_ROLE,
		------------------------------------------- TFMC TAX NUM ------------------------------------------------------------
		CAST(TFMC_TAX_NUM AS VARCHAR(99)) AS TFMC_TAX_NUM,
		--------------------------------------------- SIGNATORY 1 ----------------------------------------------------
		 CAST(SIGNATORY1_IS_PRIMARY AS VARCHAR(10)) AS SIGNATORY1_IS_PRIMARY,
		CAST(SIGNATORY1_GNDR AS VARCHAR(10)) AS SIGNATORY1_GNDR,
		CAST(SIGNATORY1_TITL AS VARCHAR(10)) AS SIGNATORY1_TITL,
		CAST(SIGNATORY1_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY1_FIRSTNAME,
		CAST(SIGNATORY1_LASTNAME AS VARCHAR(99)) AS SIGNATORY1_LASTNAME,
		CAST(SIGNATORY1_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY1_FATHER_NAME,
		CAST(SIGNATORY1_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY1_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY1_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY1_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY1_SSN,   
	    CAST(SIGNATORY1_nationality1 AS VARCHAR(10)) AS SIGNATORY1_nationality1,
	    CAST(SIGNATORY1_Residence AS VARCHAR(10)) AS SIGNATORY1_Residence,
	    CAST(SIGNATORY1_tph_contact_type AS VARCHAR(10)) AS SIGNATORY1_tph_contact_type,
	    CAST(SIGNATORY1_tph_communication_type AS VARCHAR(10)) AS SIGNATORY1_tph_communication_type,	
	    CAST(SIGNATORY1_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY1_tph_country_prefix,
		CAST(CASE WHEN SIGNATORY1_TPH_NUMBER IS NULL OR SIGNATORY1_TPH_NUMBER = '' THEN 
                  COALESCE(CASE WHEN DIR1_TPH_NUMBER IS NULL OR DIR1_TPH_NUMBER = '' THEN TTMC_tph_number END, DIR1_TPH_NUMBER ) ELSE SIGNATORY1_TPH_NUMBER END AS VARCHAR(50)) AS SIGNATORY1_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY1_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY1_DATE_OF_BIRTH, 3) ELSE SIGNATORY1_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY1_DATE_OF_BIRTH,
	    CAST(SIGNATORY1_address_type AS VARCHAR(20)) AS SIGNATORY1_address_type,
		CAST(SIGNATORY1_ADDRESS AS VARCHAR(99)) AS SIGNATORY1_ADDRESS,
	    CAST(SIGNATORY1_CITY AS VARCHAR(20)) AS SIGNATORY1_CITY,
	    CAST(SIGNATORY1_country_code AS VARCHAR(10)) AS SIGNATORY1_country_code,
	    CAST(SIGNATORY1_STATE AS VARCHAR(20)) AS SIGNATORY1_STATE,
		CAST(SIGNATORY1_OCCUPATION AS VARCHAR(99)) AS SIGNATORY1_OCCUPATION,
	    CAST(SIGNATORY1_ROLE AS VARCHAR(10)) AS SIGNATORY1_ROLE,
		--------------------------------------------- SIGNATORY 2 ----------------------------------------------------
	    CAST(CASE WHEN SIGNATORY2_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY2_IS_PRIMARY END AS VARCHAR(10)) AS SIGNATORY2_IS_PRIMARY,
		CAST(SIGNATORY2_GNDR AS VARCHAR(10)) AS SIGNATORY2_GNDR,
		CAST(SIGNATORY2_TITL AS VARCHAR(10)) AS SIGNATORY2_TITL,
		CAST(SIGNATORY2_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY2_FIRSTNAME,
		CAST(SIGNATORY2_LASTNAME AS VARCHAR(99)) AS SIGNATORY2_LASTNAME,
		CAST(SIGNATORY2_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY2_FATHER_NAME,
		CAST(SIGNATORY2_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY2_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY2_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY2_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY2_SSN,
	    CAST(SIGNATORY2_nationality1 AS VARCHAR(10)) AS SIGNATORY2_nationality1,
	    CAST(SIGNATORY2_Residence AS VARCHAR(10)) AS SIGNATORY2_Residence,
	    CAST(SIGNATORY2_tph_contact_type AS VARCHAR(10)) AS SIGNATORY2_tph_contact_type,
	    CAST(SIGNATORY2_tph_communication_type AS VARCHAR(10)) AS SIGNATORY2_tph_communication_type,	
	    CAST(SIGNATORY2_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY2_tph_country_prefix,
		CAST(SIGNATORY2_TPH_NUMBER AS VARCHAR(50)) AS SIGNATORY2_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY2_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY2_DATE_OF_BIRTH, 3) ELSE SIGNATORY2_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY2_DATE_OF_BIRTH,
	    CAST(SIGNATORY2_address_type AS VARCHAR(20)) AS SIGNATORY2_address_type,
		CAST(SIGNATORY2_ADDRESS AS VARCHAR(99)) AS SIGNATORY2_ADDRESS,
	    CAST(SIGNATORY2_CITY AS VARCHAR(20)) AS SIGNATORY2_CITY,
	    CAST(SIGNATORY2_country_code AS VARCHAR(10)) AS SIGNATORY2_country_code,
	    CAST(SIGNATORY2_STATE AS VARCHAR(20)) AS SIGNATORY2_STATE,
		CAST(SIGNATORY2_OCCUPATION AS VARCHAR(99)) AS SIGNATORY2_OCCUPATION,
	    CAST(CASE WHEN SIGNATORY2_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY2_ROLE END AS VARCHAR(10)) AS SIGNATORY2_ROLE,
        --------------------------------------------- SIGNATORY 3 ----------------------------------------------------
	    CAST(CASE WHEN SIGNATORY3_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY3_IS_PRIMARY END AS VARCHAR(10)) AS SIGNATORY3_IS_PRIMARY,
		CAST(SIGNATORY3_GNDR AS VARCHAR(10)) AS SIGNATORY3_GNDR,
		CAST(SIGNATORY3_TITL AS VARCHAR(10)) AS SIGNATORY3_TITL,
		CAST(SIGNATORY3_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY3_FIRSTNAME,
		CAST(SIGNATORY3_LASTNAME AS VARCHAR(99)) AS SIGNATORY3_LASTNAME,
		CAST(SIGNATORY3_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY3_FATHER_NAME,
		CAST(SIGNATORY3_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY3_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY3_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY3_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY3_SSN,
	    CAST(SIGNATORY3_nationality1 AS VARCHAR(10)) AS SIGNATORY3_nationality1,
	    CAST(SIGNATORY3_Residence AS VARCHAR(10)) AS SIGNATORY3_Residence,
	    CAST(SIGNATORY3_tph_contact_type AS VARCHAR(10)) AS SIGNATORY3_tph_contact_type,
	    CAST(SIGNATORY3_tph_communication_type AS VARCHAR(10)) AS SIGNATORY3_tph_communication_type,	
	    CAST(SIGNATORY3_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY3_tph_country_prefix,
		CAST(SIGNATORY3_TPH_NUMBER AS VARCHAR(50)) AS SIGNATORY3_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY3_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY3_DATE_OF_BIRTH, 3) ELSE SIGNATORY3_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY3_DATE_OF_BIRTH,
	    CAST(SIGNATORY3_address_type AS VARCHAR(20)) AS SIGNATORY3_address_type,
		CAST(SIGNATORY3_ADDRESS AS VARCHAR(99)) AS SIGNATORY3_ADDRESS,
	    CAST(SIGNATORY3_CITY AS VARCHAR(20)) AS SIGNATORY3_CITY,
	    CAST(SIGNATORY3_country_code AS VARCHAR(10)) AS SIGNATORY3_country_code,
	    CAST(SIGNATORY3_STATE AS VARCHAR(20)) AS SIGNATORY3_STATE,
		CAST(SIGNATORY3_OCCUPATION AS VARCHAR(99)) AS SIGNATORY3_OCCUPATION,
	    CAST(CASE WHEN SIGNATORY3_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY3_ROLE END AS VARCHAR(10)) AS SIGNATORY3_ROLE,
		--------------------------------------------- SIGNATORY 4 ----------------------------------------------------
	    CAST(CASE WHEN SIGNATORY4_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY4_IS_PRIMARY END AS VARCHAR(10)) AS SIGNATORY4_IS_PRIMARY,
		CAST(SIGNATORY4_GNDR AS VARCHAR(10)) AS SIGNATORY4_GNDR,
		CAST(SIGNATORY4_TITL AS VARCHAR(10)) AS SIGNATORY4_TITL,
		CAST(SIGNATORY4_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY4_FIRSTNAME,
		CAST(SIGNATORY4_LASTNAME AS VARCHAR(99)) AS SIGNATORY4_LASTNAME,
		CAST(SIGNATORY4_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY4_FATHER_NAME,
		CAST(SIGNATORY4_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY4_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY4_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY4_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY4_SSN,
	    CAST(SIGNATORY4_nationality1 AS VARCHAR(10)) AS SIGNATORY4_nationality1,
	    CAST(SIGNATORY4_Residence AS VARCHAR(10)) AS SIGNATORY4_Residence,
	    CAST(SIGNATORY4_tph_contact_type AS VARCHAR(10)) AS SIGNATORY4_tph_contact_type,
	    CAST(SIGNATORY4_tph_communication_type AS VARCHAR(10)) AS SIGNATORY4_tph_communication_type,	
	    CAST(SIGNATORY4_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY4_tph_country_prefix,
		CAST(SIGNATORY4_TPH_NUMBER AS VARCHAR(50)) AS SIGNATORY4_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY4_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY4_DATE_OF_BIRTH, 3) ELSE SIGNATORY4_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY4_DATE_OF_BIRTH,
	    CAST(SIGNATORY4_address_type AS VARCHAR(20)) AS SIGNATORY4_address_type,
		CAST(SIGNATORY4_ADDRESS AS VARCHAR(99)) AS SIGNATORY4_ADDRESS,
	    CAST(SIGNATORY4_CITY AS VARCHAR(20)) AS SIGNATORY4_CITY,
	    CAST(SIGNATORY4_country_code AS VARCHAR(10)) AS SIGNATORY4_country_code,
	    CAST(SIGNATORY4_STATE AS VARCHAR(20)) AS SIGNATORY4_STATE,
		CAST(SIGNATORY4_OCCUPATION AS VARCHAR(99)) AS SIGNATORY4_OCCUPATION,
	    CAST(CASE WHEN SIGNATORY4_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY4_ROLE END AS VARCHAR(10)) AS SIGNATORY4_ROLE,
		--------------------------------------------- SIGNATORY 5 ----------------------------------------------------
	    CAST(CASE WHEN SIGNATORY5_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY5_IS_PRIMARY END AS VARCHAR(10)) AS SIGNATORY5_IS_PRIMARY,
		CAST(SIGNATORY5_GNDR AS VARCHAR(10)) AS SIGNATORY5_GNDR,
		CAST(SIGNATORY5_TITL AS VARCHAR(10)) AS SIGNATORY5_TITL,
		CAST(SIGNATORY5_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY5_FIRSTNAME,
		CAST(SIGNATORY5_LASTNAME AS VARCHAR(99)) AS SIGNATORY5_LASTNAME,
		CAST(SIGNATORY5_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY5_FATHER_NAME,
		CAST(SIGNATORY5_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY5_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY5_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY5_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY5_SSN,
	    CAST(SIGNATORY5_nationality1 AS VARCHAR(10)) AS SIGNATORY5_nationality1,
	    CAST(SIGNATORY5_Residence AS VARCHAR(10)) AS SIGNATORY5_Residence,
	    CAST(SIGNATORY5_tph_contact_type AS VARCHAR(10)) AS SIGNATORY5_tph_contact_type,
	    CAST(SIGNATORY5_tph_communication_type AS VARCHAR(10)) AS SIGNATORY5_tph_communication_type,	
	    CAST(SIGNATORY5_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY5_tph_country_prefix,
		CAST(SIGNATORY5_TPH_NUMBER AS VARCHAR(50)) AS SIGNATORY5_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY5_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY5_DATE_OF_BIRTH, 3) ELSE SIGNATORY5_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY5_DATE_OF_BIRTH,
	    CAST(SIGNATORY5_address_type AS VARCHAR(20)) AS SIGNATORY5_address_type,
		CAST(SIGNATORY5_ADDRESS AS VARCHAR(99)) AS SIGNATORY5_ADDRESS,
	    CAST(SIGNATORY5_CITY AS VARCHAR(20)) AS SIGNATORY5_CITY,
	    CAST(SIGNATORY5_country_code AS VARCHAR(10)) AS SIGNATORY5_country_code,
	    CAST(SIGNATORY5_STATE AS VARCHAR(20)) AS SIGNATORY5_STATE,
		CAST(SIGNATORY5_OCCUPATION AS VARCHAR(99)) AS SIGNATORY5_OCCUPATION,
	    CAST(CASE WHEN SIGNATORY5_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY5_ROLE END AS VARCHAR(10)) AS SIGNATORY5_ROLE,
		--------------------------------------------- SIGNATORY 6 ----------------------------------------------------
	    CAST(CASE WHEN SIGNATORY6_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY6_IS_PRIMARY END AS VARCHAR(10)) AS SIGNATORY6_IS_PRIMARY,
		CAST(SIGNATORY6_GNDR AS VARCHAR(10)) AS SIGNATORY6_GNDR,
		CAST(SIGNATORY6_TITL AS VARCHAR(10)) AS SIGNATORY6_TITL,
		CAST(SIGNATORY6_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY6_FIRSTNAME,
		CAST(SIGNATORY6_LASTNAME AS VARCHAR(99)) AS SIGNATORY6_LASTNAME,
		CAST(SIGNATORY6_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY6_FATHER_NAME,
		CAST(SIGNATORY6_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY6_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY6_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY6_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY6_SSN,
	    CAST(SIGNATORY6_nationality1 AS VARCHAR(10)) AS SIGNATORY6_nationality1,
	    CAST(SIGNATORY6_Residence AS VARCHAR(10)) AS SIGNATORY6_Residence,
	    CAST(SIGNATORY6_tph_contact_type AS VARCHAR(10)) AS SIGNATORY6_tph_contact_type,
	    CAST(SIGNATORY6_tph_communication_type AS VARCHAR(10)) AS SIGNATORY6_tph_communication_type,	
	    CAST(SIGNATORY6_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY6_tph_country_prefix,
		CAST(SIGNATORY6_TPH_NUMBER AS VARCHAR(50)) AS SIGNATORY6_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY6_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY6_DATE_OF_BIRTH, 3) ELSE SIGNATORY6_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY6_DATE_OF_BIRTH,
	    CAST(SIGNATORY6_address_type AS VARCHAR(20)) AS SIGNATORY6_address_type,
		CAST(SIGNATORY6_ADDRESS AS VARCHAR(99)) AS SIGNATORY6_ADDRESS,
	    CAST(SIGNATORY6_CITY AS VARCHAR(20)) AS SIGNATORY6_CITY,
	    CAST(SIGNATORY6_country_code AS VARCHAR(10)) AS SIGNATORY6_country_code,
	    CAST(SIGNATORY6_STATE AS VARCHAR(20)) AS SIGNATORY6_STATE,
		CAST(SIGNATORY6_OCCUPATION AS VARCHAR(99)) AS SIGNATORY6_OCCUPATION,
	    CAST(CASE WHEN SIGNATORY6_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY6_ROLE END AS VARCHAR(10)) AS SIGNATORY6_ROLE,
		--------------------------------------------- SIGNATORY 7 ----------------------------------------------------
	    CAST(CASE WHEN SIGNATORY7_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY7_IS_PRIMARY END AS VARCHAR(10)) AS SIGNATORY7_IS_PRIMARY,
		CAST(SIGNATORY7_GNDR AS VARCHAR(10)) AS SIGNATORY7_GNDR,
		CAST(SIGNATORY7_TITL AS VARCHAR(10)) AS SIGNATORY7_TITL,
		CAST(SIGNATORY7_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY7_FIRSTNAME,
		CAST(SIGNATORY7_LASTNAME AS VARCHAR(99)) AS SIGNATORY7_LASTNAME,
		CAST(SIGNATORY7_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY7_FATHER_NAME,
		CAST(SIGNATORY7_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY7_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY7_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY7_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY7_SSN,
	    CAST(SIGNATORY7_nationality1 AS VARCHAR(10)) AS SIGNATORY7_nationality1,
	    CAST(SIGNATORY7_Residence AS VARCHAR(10)) AS SIGNATORY7_Residence,
	    CAST(SIGNATORY7_tph_contact_type AS VARCHAR(10)) AS SIGNATORY7_tph_contact_type,
	    CAST(SIGNATORY7_tph_communication_type AS VARCHAR(10)) AS SIGNATORY7_tph_communication_type,	
	    CAST(SIGNATORY7_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY7_tph_country_prefix,
		CAST(SIGNATORY7_TPH_NUMBER AS VARCHAR(50)) AS SIGNATORY7_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY7_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY7_DATE_OF_BIRTH, 3) ELSE SIGNATORY7_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY7_DATE_OF_BIRTH,
	    CAST(SIGNATORY7_address_type AS VARCHAR(20)) AS SIGNATORY7_address_type,
		CAST(SIGNATORY7_ADDRESS AS VARCHAR(99)) AS SIGNATORY7_ADDRESS,
	    CAST(SIGNATORY7_CITY AS VARCHAR(20)) AS SIGNATORY7_CITY,
	    CAST(SIGNATORY7_country_code AS VARCHAR(10)) AS SIGNATORY7_country_code,
	    CAST(SIGNATORY7_STATE AS VARCHAR(20)) AS SIGNATORY7_STATE,
		CAST(SIGNATORY7_OCCUPATION AS VARCHAR(99)) AS SIGNATORY7_OCCUPATION,
	    CAST(CASE WHEN SIGNATORY7_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY7_ROLE END AS VARCHAR(10)) AS SIGNATORY7_ROLE,
		--------------------------------------------- SIGNATORY 8 ----------------------------------------------------
	    CAST(CASE WHEN SIGNATORY8_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY8_IS_PRIMARY END AS VARCHAR(10)) AS SIGNATORY8_IS_PRIMARY,
		CAST(SIGNATORY8_GNDR AS VARCHAR(10)) AS SIGNATORY8_GNDR,
		CAST(SIGNATORY8_TITL AS VARCHAR(10)) AS SIGNATORY8_TITL,
		CAST(SIGNATORY8_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY8_FIRSTNAME,
		CAST(SIGNATORY8_LASTNAME AS VARCHAR(99)) AS SIGNATORY8_LASTNAME,
		CAST(SIGNATORY8_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY8_FATHER_NAME,
		CAST(SIGNATORY8_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY8_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY8_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY8_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY8_SSN,
	    CAST(SIGNATORY8_nationality1 AS VARCHAR(10)) AS SIGNATORY8_nationality1,
	    CAST(SIGNATORY8_Residence AS VARCHAR(10)) AS SIGNATORY8_Residence,
	    CAST(SIGNATORY8_tph_contact_type AS VARCHAR(10)) AS SIGNATORY8_tph_contact_type,
	    CAST(SIGNATORY8_tph_communication_type AS VARCHAR(10)) AS SIGNATORY8_tph_communication_type,	
	    CAST(SIGNATORY8_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY8_tph_country_prefix,
		CAST(SIGNATORY8_TPH_NUMBER AS VARCHAR(50)) AS SIGNATORY8_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY8_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY8_DATE_OF_BIRTH, 3) ELSE SIGNATORY8_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY8_DATE_OF_BIRTH,
	    CAST(SIGNATORY8_address_type AS VARCHAR(20)) AS SIGNATORY8_address_type,
		CAST(SIGNATORY8_ADDRESS AS VARCHAR(99)) AS SIGNATORY8_ADDRESS,
	    CAST(SIGNATORY8_CITY AS VARCHAR(20)) AS SIGNATORY8_CITY,
	    CAST(SIGNATORY8_country_code AS VARCHAR(10)) AS SIGNATORY8_country_code,
	    CAST(SIGNATORY8_STATE AS VARCHAR(20)) AS SIGNATORY8_STATE,
		CAST(SIGNATORY8_OCCUPATION AS VARCHAR(99)) AS SIGNATORY8_OCCUPATION,
	    CAST(CASE WHEN SIGNATORY8_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY8_ROLE END AS VARCHAR(10)) AS SIGNATORY8_ROLE,
		----------------------------------------- TFMC REMAINGING ---------------------------------------------------------
		CAST(TFMC_open AS VARCHAR(20)) AS TFMC_open,
		CAST(TFMC_status_code AS VARCHAR(10)) AS TFMC_status_code,
		CAST(TFMC_from_country AS VARCHAR(10)) AS TFMC_from_country,
		--------------------------------------- TO MY CLEINT TAG -----------------------------------------------------------
		CAST(TTMC_to_funds_code AS VARCHAR(10)) AS TTMC_to_funds_code,
		CAST(TTMC_Gender AS VARCHAR(10)) AS TTMC_Gender,
		CAST(TTMC_Title AS VARCHAR(99)) AS TTMC_Title,
		CAST(TTMC_First_Name AS VARCHAR(99)) AS TTMC_First_Name,
		CAST(TTMC_Last_Name AS VARCHAR(99)) AS TTMC_Last_Name,
		CAST(CASE WHEN TTMC_Birth_Date LIKE '00%'  THEN '19' || SUBSTR(TTMC_Birth_Date, 3) ELSE TTMC_Birth_Date END AS VARCHAR(20)) AS TTMC_Birth_Date,
		CAST(TTMC_Mother_Name AS VARCHAR(99)) AS TTMC_Mother_Name,
		CAST(TTMC_ssn_type AS VARCHAR(10)) AS TTMC_ssn_type,
		CAST(CASE WHEN TTMC_ssn_type IN ('NIC', 'PPT', 'POC') THEN TTMC_ssn ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS TTMC_ssn,		
		CAST(CASE WHEN TTMC_ssn_type= 'NIC' THEN 'PK' ELSE TTMC_nationality1 END  AS VARCHAR(20)) AS TTMC_nationality1, 
		CAST(TTMC_Residence AS VARCHAR(20)) AS TTMC_Residence,
		CAST(TTMC_tph_contact_type AS VARCHAR(20)) AS TTMC_tph_contact_type,
		CAST(TTMC_tph_communication_type AS VARCHAR(20)) AS TTMC_tph_communication_type,
		CAST(TTMC_tph_country_prefix AS VARCHAR(10)) AS TTMC_tph_country_prefix,
		CAST(TTMC_tph_number AS VARCHAR(20)) AS TTMC_tph_number,
		CAST(TTMC_address_type AS VARCHAR(10)) AS TTMC_address_type,
		CAST(TTMC_address AS VARCHAR(99)) AS TTMC_address,
		CAST(TTMC_city AS VARCHAR(50)) AS TTMC_city,
		CAST(TTMC_country_code AS VARCHAR(10)) AS TTMC_country_code,
		CAST(TTMC_state AS VARCHAR(50)) AS TTMC_state,
		CAST(TTMC_occupation AS VARCHAR(99)) AS TTMC_occupation,
		CAST(TTMC_to_country AS VARCHAR(20)) AS TTMC_to_country
		FROM Final_Chunk 
		) 
		

		SELECT * FROM DATA_V1 
		WHERE CATEGORY = '{entity_individual_flag}' ;
		
		

	
	"""
	return query



def get_cash_withdrawal_query(trxn_date, entity_individual_flag):

	query = rf"""WITH ENTITY AS (
		SELECT
		FCT.TSACTN_ID,
		FCT.ACCT_SROGT_ID
		FROM DP_SDMVW_DFDN.FCT_RTAIL_BNK_TSACTN_VW FCT
		INNER JOIN DP_SDMVW_DFDN.DIM_RTAIL_BNK_ACCT_VW ACCT ON ACCT.ACCT_SROGT_ID = FCT.ACCT_SROGT_ID
		LEFT JOIN (select CURY_EDW_ID, EXCH_RATE as CCY_RATE FROM  DP_SDMVW_DFDN.FCT_CURY_EXCH_RATE_VW where BATCH_DT = '{trxn_date}') EXC
		ON FCT.CURY_EDW_ID = EXC.CURY_EDW_ID
		WHERE 1=1
		-- AND FCT.TSACTN_ID IN ()
		AND FCT.TSACTN_TYPE_EDW_ID IN ('0001','0201','0006')
		AND FCT.TSACTN_DT BETWEEN '{trxn_date}' AND '{trxn_date}'
		AND CASE WHEN EXC.CURY_EDW_ID IS NOT NULL THEN FCT.TSACTN_AMT * CCY_RATE ELSE FCT.TSACTN_AMT END >= '2000000'
		AND 
		( 
		ACCT.CUST_TYPE_EDW_ID IN ( '63','51','36','31','61','34','53','37','35','65','33','32','55','62','64','54','52') 
		OR
		EXISTS(
		SELECT 1 FROM DP_SDMVW_DFDN.DIM_CTR_Keywords_VW t 
		WHERE t.flag = 'NO' AND ACCT.ACCT_TITL LIKE '%' || t.keyword || '%'
		)
		OR 
		EXISTS(
		SELECT 1 FROM DP_SDMVW_DFDN.DIM_CTR_Keywords_VW t 
		WHERE t.flag = 'YES' AND REGEXP_INSTR(ACCT.ACCT_TITL, '(^|[^A-Z0-9])' || t.keyword || '([^A-Z0-9]|$)', 1,1,0, 'i') > 0
		)
		)
		AND FCT.CR_DR_IND = 'D'
		AND FCT.RVSL_SEQ_NUM IS NULL
		AND FCT.Reveral_IND = 'N'
		AND FCT.TRAC_ID IS NULL
		)

		,TRXNS AS (
		SELECT
		FCT.*, 
		CASE WHEN FCT.CURY_EDW_ID <> 'PKR' THEN FCT.CURY_EDW_ID ELSE CAST(NULL AS VARCHAR(10)) END AS FRGN_CCY,
		CASE WHEN FCT.CURY_EDW_ID <> 'PKR' THEN CAST(FCT.TSACTN_AMT AS INT) ELSE CAST(NULL AS VARCHAR(10)) END AS FRGN_TSACTN_AMT,
		CASE WHEN FCT.CURY_EDW_ID <> 'PKR' THEN EXC.CCY_RATE ELSE CAST(NULL AS VARCHAR(10)) END AS EXCHANGE_RATE,
		FCT.TSACTN_AMT * EXC.CCY_RATE AS FRGN_TSACTN_AMT_PKR,
		ACCT.ACCT_TITL,
		ACCT.ACCT_SROGT_ID AS ACCOUNT_SROGT_ID, ACCT.CUST_TYPE_EDW_ID AS ACCOUNT_CUST_TYPE_EDW_ID , ACCT.BRNCH_SROGT_ID AS ACCT_BRNCH_SROGT_ID ,
		ACCT.ACCT_ORIGNL_OPN_DT , ACCT.ACCT_DESC, ACCT.CURY_EDW_ID AS ACCT_CURY_EDW_ID,
		PROD.ACCT_TYPE_DESC,
		--PROD.CODE AS ACCT_TYPE_CODE ,
		CASE WHEN REGEXP_SIMILAR(UPPER(ACCT.ACCT_TITL), '.*(^|[^A-Z0-9])CDC([^A-Z0-9]|$).*') = 1 THEN 'ATSAV' ELSE PROD.CODE END AS ACCT_TYPE_CODE,
		COD.CATEGORY_TYPE_DESC,
		COD.CODE AS CATEGORY_TYPE_CODE,
		CASE WHEN E.ACCT_SROGT_ID IS NOT NULL THEN 'ENTITY' ELSE 'INDIVIDUAL' END AS CATEGORY
		
		FROM DP_SDMVW_DFDN.FCT_RTAIL_BNK_TSACTN_VW FCT
		INNER JOIN DP_SDMVW_DFDN.DIM_RTAIL_BNK_ACCT_VW ACCT ON ACCT.ACCT_SROGT_ID = FCT.ACCT_SROGT_ID
		LEFT JOIN ENTITY E ON FCT.TSACTN_ID = E.TSACTN_ID 
		LEFT JOIN DP_SDMT_DFDN.DIM_CTR_ACCT_TYPE prod ON ACCT.PROD_SROGT_ID = prod.ACCT_TYPE 
		LEFT JOIN DP_SDMT_DFDN.DIM_CTR_CATEGORY_CODES COD ON ACCT.CUST_TYPE_EDW_ID = COD.CATEGORY_TYPE
		LEFT JOIN (select CURY_EDW_ID, EXCH_RATE as CCY_RATE FROM  DP_SDMVW_DFDN.FCT_CURY_EXCH_RATE_VW where BATCH_DT = '{trxn_date}') EXC
		ON FCT.CURY_EDW_ID = EXC.CURY_EDW_ID
		WHERE 1=1
		-- AND FCT.TSACTN_ID IN ()
		AND FCT.TSACTN_TYPE_EDW_ID IN ('0001','0201','0006')
		AND FCT.TSACTN_DT BETWEEN '{trxn_date}' AND '{trxn_date}'
		AND CASE WHEN EXC.CURY_EDW_ID IS NOT NULL THEN FCT.TSACTN_AMT * CCY_RATE ELSE FCT.TSACTN_AMT END >= '2000000'
		AND FCT.CR_DR_IND = 'D'
		AND FCT.RVSL_SEQ_NUM IS NULL
		AND FCT.Reveral_IND = 'N'
		AND FCT.TRAC_ID IS NULL
		)
		
	-- DP_REPORTING_MART.TM_DM_MD_MANDATE_AUTHORIZE
    , MANDATE AS (
		SELECT x.*,
	    ROW_NUMBER() OVER(PARTITION BY ACCT_SROGT_ID ORDER BY M_DT_OF_BIRTH DESC) AS M_RN
	    FROM (
			SELECT
			    T.ACCT_SROGT_ID,
			    T.TSACTN_ID,
			    M.CLIENT_NO AS M_CLIENT_NO,
				'TRUE' AS M_IS_PRIMARY, 
				CASE 
					 WHEN MC.GNDR IS NOT NULL THEN MC.GNDR
					 WHEN MC.GNDR IS NULL THEN 
								CASE WHEN RIGHT(MC.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(MC.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'M' 
								WHEN RIGHT(MC.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(MC.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'F' 
								ELSE CAST(NULL AS VARCHAR(10)) END END AS M_GNDR,			
				CASE 
					 WHEN MC.TITL IS NOT NULL THEN MC.TITL
					 WHEN MC.TITL IS NULL THEN 
								CASE WHEN RIGHT(MC.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(MC.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'MR' 
								WHEN RIGHT(MC.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(MC.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'MS'
								ELSE CAST(NULL AS VARCHAR(10)) END END AS M_TITL, 			

			    TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
						FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) )  AS  M_FRST_NAME,
				
				CASE WHEN  REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0 
							THEN  TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
				              			  POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) )
							ELSE 
									CASE WHEN (MC.FRST_NAME IS NULL AND MC.MDL_NAME IS NULL AND MC.LAST_NAME IS NULL) OR (MC.FRST_NAME = '' AND MC.MDL_NAME = '' AND MC.LAST_NAME = '')
												THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
												 			FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
												ELSE 
														CASE WHEN REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(MC.FRST_NAME, '') || ' ' || COALESCE(MC.MDL_NAME, '') || ' ' || COALESCE(MC.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0
																	THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(MC.FRST_NAME, '') || ' ' || COALESCE(MC.MDL_NAME, '') || ' ' || COALESCE(MC.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
													            				POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(MC.FRST_NAME, '') || ' ' || COALESCE(MC.MDL_NAME, '') || ' ' || COALESCE(MC.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) 
														ELSE TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
																 	FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
														END
									END
				END	AS M_LAST_NAME ,
				
			    TO_CHAR(MC.DT_OF_BIRTH , 'YYYY-MM-DD') ||  'T00:00:00' AS M_DT_OF_BIRTH,
				TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.FTHR_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) AS M_MOTHER_NAME,
				
				MC.IDNTFTN_TYPE_EDW_ID AS M_SSN_TYPE,
				CASE WHEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) = '' THEN CAST(NULL AS VARCHAR(10)) 
							   ELSE TRIM(REGEXP_REPLACE(REGEXP_REPLACE(MC.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) END AS M_SSN,
			     CASE
					when MC.MBL_NUM is not null AND MC.MBL_NUM <> ''  
					THEN CASE WHEN REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(MC.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' ) IS NULL OR REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(MC.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' ) = ''
								THEN TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(MC.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') ) ELSE REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(MC.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' )  END
			        when MC.PHN_RSDNC is not null AND MC.PHN_RSDNC <> '' then TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(MC.PHN_RSDNC), '[^ ]+', 1, 1), '[^0-9]', '') )
			        else 
					case 
						WHEN REGEXP_SIMILAR(MC.PHN_BUSN, '.*[A-Za-z].*') = '1' AND REGEXP_SIMILAR(MC.PHN_BUSN, '.*[0-9].*') = '1' THEN CAST(NULL AS VARCHAR(11))
						WHEN REGEXP_SIMILAR(MC.PHN_BUSN, '.*[A-Za-z].*') = '1' THEN CAST(NULL AS VARCHAR(11))
						ELSE 
							case
								when substr(regexp_replace(MC.PHN_BUSN, '[^0-9]', ''), 1,3) = '092' then substr(regexp_replace(MC.PHN_BUSN, '[^0-9]', ''), 3) 
								when substr(regexp_replace(MC.PHN_BUSN, '[^0-9]', ''), 1,2) = '92' then substr(regexp_replace(MC.PHN_BUSN, '[^0-9]', ''), 3)  
								ELSE trim(LEADING '0' FROM regexp_replace(MC.PHN_BUSN, '[^0-9]', ''))
							end
					end 
				END as M_tph_number,      	
				
				TRIM(OREPLACE(OREPLACE(
				CASE 
				WHEN TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is not null AND TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3
				              THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' ')  , '[[:space:]]+', ' '))  
				WHEN (TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
						       AND (TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
						      THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' ')) 
				WHEN (TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
						       AND ( TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(MC.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))
				WHEN (TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3 ) 
						       AND (TRIM(REGEXP_REPLACE(TRIM(MC.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(MC.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(MC.OTH_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(MC.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))		   
				ELSE CAST(NULL AS VARCHAR(10)) 
				END
				,CHR(13),' '),CHR(10), ' ')) as M_address,

			    CASE WHEN _MDO.OCPTN_DESC IS NOT NULL OR _MDO.OCPTN_DESC <> '' THEN _MDO.OCPTN_DESC ELSE 'Others' END AS M_OCCUPATION,
				
				MC.CTRY_OF_NTLTY as M_nationality1,
				'PK' as M_Residence,
				CASE WHEN MC.MBL_NUM is not null AND MC.MBL_NUM <> '' then 'PAPVT' when MC.MBL_NUM is null OR MC.MBL_NUM = '' then 'PAOFF' END as M_tph_contact_type,
				CASE WHEN MC.MBL_NUM is not null AND MC.MBL_NUM <> '' then 'COMOB' else 'COLAN' END as M_tph_communication_type,
				'92' as M_tph_country_prefix,
				
				CASE WHEN MC.PERM_ADDR is not null and MC.PERM_ADDR <> '' then 'PAPVT' 
							when MC.PERM_ADDR is null OR MC.PERM_ADDR = '' then 'PAOFF' END as M_address_type,
				
				CASE WHEN TRIM(MC.RSDNTL_CITY) = '0' THEN CAST(NULL AS VARCHAR(10)) ELSE MC.RSDNTL_CITY END AS M_city, 
				
				'PK' as M_country_code,
				CASE  
				when substr(MC.IDNTFTN_VAL,1,1) IN ('1', '2') then 'KHYBER-PAKHTUNKHWA'
				when substr(MC.IDNTFTN_VAL,1,1) IN ('3', '6') then 'PUNJAB'
				when substr(MC.IDNTFTN_VAL,1,1) = '4' then 'SINDH'
				when substr(MC.IDNTFTN_VAL,1,1) = '5' then 'BALOCHISTAN'
				when substr(MC.IDNTFTN_VAL,1,1) = '7' then 'GILGIT-BALISTAN'
				when substr(MC.IDNTFTN_VAL,1,1) = '8' then 'AZAD-KASHMIR'
				ELSE cast(null as varchar(10)) 
				END as M_state,
				
				'ARPYS' AS M_role
				
			    ,ROW_NUMBER() OVER(PARTITION BY M.CLIENT_NO ORDER BY M.CLIENT_NO) AS RN
		    FROM  TRXNS T
		    INNER JOIN DP_REPORTING_MART.TM_DM_MD_MANDATE_AUTHORIZE M ON T.ACCT_SROGT_ID = M.ACCT_NO  -- DP_SDMVW_DFDN.TM_DM_MD_MANDATE_AUTHORIZE_VW 
		    LEFT JOIN DP_SDMVW_DFDN.DIM_CUST_VW MC ON MC.CUST_SROGT_ID = M.CLIENT_NO AND MC.SYSTEM_CODE = 'CBS'
		    LEFT JOIN DP_SDMT_DFDN.DIM_OCPTN_SS _MDO ON MC.OCPTN_EDW_ID = _MDO.OCPTN_EDW_ID
		    WHERE 1=1 AND M.START_DATE = (SELECT CAST(MAX(START_DATE) AS DATE) AS START_DATE FROM DP_REPORTING_MART.TM_DM_MD_MANDATE_AUTHORIZE)
			 -- CAST(CURRENT_DATE - 1 AS DATE)
			
	    ) AS X
    WHERE 1=1
  	AND X.RN = 1
	)
		
		                             
	-- DP_REPORTING_MART.FM_DIRECTOR_DTLS
	, DIRECTORS AS (
		SELECT x.*, ROW_NUMBER() OVER(PARTITION BY CUST_SROGT_ID ORDER BY D_DT_OF_BIRTH DESC) AS D_RN
		FROM (
			SELECT 
				T.ACCT_SROGT_ID,
				T.CUST_SROGT_ID,
				T.TSACTN_ID,
				DC.CUST_SROGT_ID AS D_CUST_SROGT_ID,
				
				CASE 
					 WHEN DC.GNDR IS NOT NULL THEN DC.GNDR
					 WHEN DC.GNDR IS NULL THEN 
								CASE WHEN RIGHT(DC.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(DC.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'M' 
								WHEN RIGHT(DC.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(DC.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'F' 
								ELSE CAST(NULL AS VARCHAR(10)) END END AS D_GNDR,			
				CASE 
					 WHEN DC.TITL IS NOT NULL THEN DC.TITL
					 WHEN DC.TITL IS NULL THEN 
								CASE WHEN RIGHT(DC.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(DC.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'MR' 
								WHEN RIGHT(DC.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(DC.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'MS'
								ELSE CAST(NULL AS VARCHAR(10)) END END AS D_TITL, 	

				TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
						FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) )  AS  D_FRST_NAME,
				
				CASE WHEN  REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0 
							THEN  TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
				              			  POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) )
							ELSE 
									CASE WHEN (DC.FRST_NAME IS NULL AND DC.MDL_NAME IS NULL AND DC.LAST_NAME IS NULL) OR (DC.FRST_NAME = '' AND DC.MDL_NAME = '' AND DC.LAST_NAME = '')
												THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
												 			FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
												ELSE 
														CASE WHEN REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(DC.FRST_NAME, '') || ' ' || COALESCE(DC.MDL_NAME, '') || ' ' || COALESCE(DC.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0
																	THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(DC.FRST_NAME, '') || ' ' || COALESCE(DC.MDL_NAME, '') || ' ' || COALESCE(DC.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
													            				POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(DC.FRST_NAME, '') || ' ' || COALESCE(DC.MDL_NAME, '') || ' ' || COALESCE(DC.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) 
														ELSE TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
																 	FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
														END
									END
				END	AS D_LAST_NAME ,
				
				TO_CHAR(DC.DT_OF_BIRTH , 'YYYY-MM-DD') ||  'T00:00:00' AS D_DT_OF_BIRTH,
				TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.FTHR_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) AS D_MOTHER_NAME,
				
				DC.IDNTFTN_TYPE_EDW_ID AS D_SSN_TYPE,
				CASE WHEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) = '' THEN CAST(NULL AS VARCHAR(10)) 
							   ELSE TRIM(REGEXP_REPLACE(REGEXP_REPLACE(DC.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) END AS D_SSN,
				 CASE
					when DC.MBL_NUM is not null AND DC.MBL_NUM <> ''  
					THEN CASE WHEN REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(DC.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' ) IS NULL OR REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(DC.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' ) = ''
								THEN TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(DC.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') ) ELSE REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(DC.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' )  END
			        when DC.PHN_RSDNC is not null AND DC.PHN_RSDNC <> '' then TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(DC.PHN_RSDNC), '[^ ]+', 1, 1), '[^0-9]', '') )
			        else 
					case 
						WHEN REGEXP_SIMILAR(DC.PHN_BUSN, '.*[A-Za-z].*') = '1' AND REGEXP_SIMILAR(DC.PHN_BUSN, '.*[0-9].*') = '1' THEN CAST(NULL AS VARCHAR(11))
						WHEN REGEXP_SIMILAR(DC.PHN_BUSN, '.*[A-Za-z].*') = '1' THEN CAST(NULL AS VARCHAR(11))
						ELSE 
							case
								when substr(regexp_replace(DC.PHN_BUSN, '[^0-9]', ''), 1,3) = '092' then substr(regexp_replace(DC.PHN_BUSN, '[^0-9]', ''), 3) 
								when substr(regexp_replace(DC.PHN_BUSN, '[^0-9]', ''), 1,2) = '92' then substr(regexp_replace(DC.PHN_BUSN, '[^0-9]', ''), 3)  
								ELSE trim(LEADING '0' FROM regexp_replace(DC.PHN_BUSN, '[^0-9]', ''))
							end
					end 
				END as D_tph_number, 	
				
				TRIM(OREPLACE(OREPLACE(
				CASE 
				WHEN TRIM(REGEXP_REPLACE(TRIM(DC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is not null AND TRIM(REGEXP_REPLACE(TRIM(DC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(DC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3
				              THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(DC.PERM_ADDR), '[^A-Za-z0-9 ]', ' ')  , '[[:space:]]+', ' '))  
				WHEN (TRIM(REGEXP_REPLACE(TRIM(DC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(DC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(DC.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
						       AND (TRIM(REGEXP_REPLACE(TRIM(DC.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(DC.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(DC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
						      THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(DC.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' ')) 
				WHEN (TRIM(REGEXP_REPLACE(TRIM(DC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(DC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(DC.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
						       AND ( TRIM(REGEXP_REPLACE(TRIM(DC.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(DC.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(DC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(DC.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))
				WHEN (TRIM(REGEXP_REPLACE(TRIM(DC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(DC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(DC.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3 ) 
						       AND (TRIM(REGEXP_REPLACE(TRIM(DC.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(DC.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(DC.OTH_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(DC.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))		   
				ELSE CAST(NULL AS VARCHAR(10)) 
				END
				,CHR(13),' '),CHR(10), ' ')) as D_address,	

				CASE WHEN _DDO.OCPTN_DESC IS NOT NULL OR _DDO.OCPTN_DESC <> '' THEN _DDO.OCPTN_DESC ELSE 'Others' END AS D_OCCUPATION,
				
				DC.CTRY_OF_NTLTY as D_nationality1,
				'PK' as D_Residence,
				CASE WHEN DC.MBL_NUM is not null AND DC.MBL_NUM <> '' then 'PAPVT' when DC.MBL_NUM is null OR DC.MBL_NUM = '' then 'PAOFF' END as D_tph_contact_type,
				CASE WHEN DC.MBL_NUM is not null AND DC.MBL_NUM <> '' then 'COMOB' else 'COLAN' END as D_tph_communication_type,
				'92' as D_tph_country_prefix,
				
				CASE WHEN DC.PERM_ADDR is not null and DC.PERM_ADDR <> '' then 'PAPVT' 
						    when DC.PERM_ADDR is null OR DC.PERM_ADDR = '' then 'PAOFF' END as D_address_type,
				
				CASE WHEN TRIM(DC.RSDNTL_CITY) = '0' THEN CAST(NULL AS VARCHAR(10)) ELSE DC.RSDNTL_CITY END AS D_city,  
				
				'PK' as D_country_code,
				CASE  
				when substr(DC.IDNTFTN_VAL,1,1) IN ('1', '2') then 'KHYBER-PAKHTUNKHWA'
				when substr(DC.IDNTFTN_VAL,1,1) IN ('3', '6') then 'PUNJAB'
				when substr(DC.IDNTFTN_VAL,1,1) = '4' then 'SINDH'
				when substr(DC.IDNTFTN_VAL,1,1) = '5' then 'BALOCHISTAN'
				when substr(DC.IDNTFTN_VAL,1,1) = '7' then 'GILGIT-BALISTAN'
				when substr(DC.IDNTFTN_VAL,1,1) = '8' then 'AZAD-KASHMIR'
				ELSE cast(null as varchar(10)) 
				END as D_state,
				
				'ERDIR' AS D_role
				
				,ROW_NUMBER() OVER(PARTITION BY DD.CLIENT_NO_DIR ORDER BY DD.CLIENT_NO_DIR) AS RN
			FROM TRXNS T
			INNER JOIN DP_REPORTING_MART.FM_DIRECTOR_DTLS DD ON T.CUST_SROGT_ID = DD.CLIENT_NO  -- DP_SDMVW_DFDN.FM_DIRECTOR_DTLS_VW 
			LEFT JOIN DP_SDMVW_DFDN.DIM_CUST_VW DC ON DC.CUST_SROGT_ID = DD.CLIENT_NO_DIR AND DC.SYSTEM_CODE = 'CBS' 
			LEFT JOIN DP_SDMT_DFDN.DIM_OCPTN_SS _DDO ON DC.OCPTN_EDW_ID = _DDO.OCPTN_EDW_ID
			WHERE 1=1 AND DD.START_DATE = (SELECT CAST(MAX(START_DATE) AS DATE) AS START_DATE FROM DP_REPORTING_MART.FM_DIRECTOR_DTLS)
			-- CAST(CURRENT_DATE - 1 AS DATE)
		) X 
	WHERE 1=1 
	AND X.RN = 1
	)
					
	, WALKIN_DETAILS AS (
		
		SELECT * FROM (
			select 
			w.Transaction_ID,
			CASE 
			 WHEN w.Cust_Type = 'AH' AND d.GNDR IS NOT NULL THEN d.GNDR
			 WHEN w.Cust_Type = 'AH' AND d.GNDR IS NULL THEN 
						CASE WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'M' 
						WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'F' 
						ELSE CAST(NULL AS VARCHAR(10)) END 
			 WHEN w.Cust_Type = 'TP' THEN
						CASE WHEN RIGHT(W_CNIC,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(W_CNIC, '-', ''), '/', '')) = 13 THEN 'M' 
						WHEN RIGHT(W_CNIC,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(W_CNIC, '-', ''), '/', '')) = 13  THEN 'F' 
						ELSE CAST(NULL AS VARCHAR(10)) END  
			END as Gender,

			CASE 
			 WHEN w.Cust_Type = 'AH' AND d.TITL IS NOT NULL THEN d.TITL
			 WHEN w.Cust_Type = 'AH' AND d.TITL IS NULL THEN 
						CASE WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'MR' 
						WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'MS'
						END 
			 WHEN w.Cust_Type = 'TP' THEN
						CASE WHEN RIGHT(W_CNIC,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(W_CNIC, '-', ''), '/', '')) = 13 THEN 'MR' 
						WHEN RIGHT(W_CNIC,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(W_CNIC, '-', ''), '/', '')) = 13  THEN 'MS' 
						ELSE CAST(NULL AS VARCHAR(10)) END  
			END as "Title",
			CASE 
			WHEN w.Cust_Type = 'AH'  THEN
			TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
							FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
			WHEN w.Cust_Type = 'TP'  THEN
			TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
							FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) )  
			END AS First_Name ,

			CASE 
			WHEN w.Cust_Type = 'AH'  THEN
				CASE WHEN  REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0 
							THEN  TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
				              			  POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) )
							ELSE 
									CASE WHEN (D.FRST_NAME IS NULL AND D.MDL_NAME IS NULL AND D.LAST_NAME IS NULL) OR (D.FRST_NAME = '' AND D.MDL_NAME = '' AND D.LAST_NAME = '')
												THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
												 			FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
												ELSE 
														CASE WHEN REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0
																	THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
													            				POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) 
														ELSE TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
																 	FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
														END
									END
				END
			WHEN w.Cust_Type = 'TP'  THEN 
				CASE  		
						 WHEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
								POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) IS NULL 
								OR 
						TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
								POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) = '' 
						THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
								FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) )
						ELSE TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
								POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w_customer_name, '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) END
			END AS Last_Name ,
			CASE WHEN w.Cust_Type = 'AH'  THEN TO_CHAR(d.DT_OF_BIRTH , 'YYYY-MM-DD') ||  'T00:00:00'  WHEN w.Cust_Type = 'TP' THEN TO_CHAR(w.BIRTH_DATE  , 'YYYY-MM-DD') ||  'T00:00:00'  END as Birth_Date,
			CASE WHEN w.Cust_Type = 'AH'  THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(d.FTHR_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) 
						 WHEN w.Cust_Type = 'TP' THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(w.FATHER_NAME , '[^A-Za-z ]', ' '), ' +', ' ')) END as Mother_Name,

			CASE WHEN w.Cust_Type = 'AH'  THEN D.IDNTFTN_TYPE_EDW_ID WHEN w.Cust_Type = 'TP' THEN 
						CASE WHEN LENGTH(REGEXP_REPLACE(w.w_cnic, '[^0-9]', '')) = 13 THEN 'NIC' 
									 WHEN REGEXP_SIMILAR( TRIM(REGEXP_REPLACE(w.w_cnic, '[^A-Za-z0-9]', '')), '^[A-Za-z0-9]+$') = 1 THEN 'PPT'  
									 ELSE CAST(NULL AS VARCHAR(10)) END
			END AS ssn_type,
			CASE WHEN w.Cust_Type = 'AH'  THEN d.IDNTFTN_VAL WHEN w.Cust_Type = 'TP' THEN w.w_cnic END as ssn,
			CASE WHEN w.Cust_Type = 'AH'  THEN d.CTRY_OF_NTLTY WHEN w.Cust_Type = 'TP' THEN 'PK' END as nationality1,
			'PK' as Residence,

			CASE WHEN w.Cust_Type = 'AH'  THEN case when d.MBL_NUM is not null AND d.MBL_NUM <> '' then 'PAPVT' when d.MBL_NUM is null OR d.MBL_NUM = '' then 'PAOFF' end
			WHEN w.Cust_Type = 'TP' THEN  'PAPVT' END as tph_contact_type,

			CASE WHEN w.Cust_Type = 'AH'  
			THEN case when d.MBL_NUM is not null AND d.MBL_NUM <> '' then 'COMOB' else 'COLAN' end
			WHEN w.Cust_Type = 'TP' THEN  'COMOB' END as tph_communication_type,

			'PK' as tph_country_prefix,
						
			CASE WHEN w.Cust_Type = 'AH'  THEN				  
			CASE
				when D.MBL_NUM is not null AND D.MBL_NUM <> ''  
				THEN CASE WHEN REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' ) IS NULL OR REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' ) = ''
							THEN TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') ) ELSE REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' )  END
		        when D.PHN_RSDNC is not null AND D.PHN_RSDNC <> '' then TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.PHN_RSDNC), '[^ ]+', 1, 1), '[^0-9]', '') )
		        else 
				case 
					WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' AND REGEXP_SIMILAR(D.PHN_BUSN, '.*[0-9].*') = '1' THEN CAST(NULL AS VARCHAR(11))
					WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' THEN CAST(NULL AS VARCHAR(11))
					ELSE 
						case
							when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,3) = '092' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3) 
							when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,2) = '92' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3)  
							ELSE trim(LEADING '0' FROM regexp_replace(D.PHN_BUSN, '[^0-9]', ''))
						end
				end 
			END		    
			WHEN w.Cust_Type = 'TP' THEN  TRIM(LEADING '0' FROM w.CONTACT_NO) END as tph_number,

			CASE WHEN w.Cust_Type = 'AH'  THEN	
			case when d.PERM_ADDR is not null and d.PERM_ADDR <> '' then 'PAPVT' 
						when d.PERM_ADDR is null or  d.PERM_ADDR = '' then 'PAOFF' end 
			WHEN w.Cust_Type = 'TP' THEN  'PAPVT' END as address_type,

			TRIM(OREPLACE(OREPLACE( 	
			CASE WHEN w.Cust_Type = 'AH'  THEN	
					CASE 
					WHEN TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is not null AND TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3
					              THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' ')  , '[[:space:]]+', ' '))  
					WHEN (TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
							       AND (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							      THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' ')) 
					WHEN (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
							       AND ( TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
								   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))
					WHEN (TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3 ) 
							       AND (TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
								   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))		   
					ELSE CAST(NULL AS VARCHAR(10)) 
					END
			WHEN w.Cust_Type = 'TP' THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(w.CUSTOMER_ADDRESS), '[^A-Za-z0-9 ]', ' ')  , '[[:space:]]+', ' ')) END ,CHR(13),' '),CHR(10), ' ')) as address,

			--CASE WHEN w.Cust_Type = 'AH'  THEN	CASE WHEN REGEXP_REPLACE(TRIM(d.RSDNTL_CITY), '[^A-Za-z ]', '') = '' THEN CAST(NULL AS VARCHAR(10)) ELSE REGEXP_REPLACE(TRIM(d.RSDNTL_CITY), '[^A-Za-z ]', '') END
			--WHEN w.Cust_Type = 'TP' THEN CAST(NULL	AS VARCHAR(10)) END as city,
			
			B.CITY_NAME AS city,

			'PK' as country_code,
			CASE WHEN w.Cust_Type = 'AH'  THEN
			case 
			when substr(d.IDNTFTN_VAL,1,1) IN ('1', '2') then 'KHYBER-PAKHTUNKHWA'
			when substr(d.IDNTFTN_VAL,1,1) IN ('3', '6') then 'PUNJAB'
			when substr(d.IDNTFTN_VAL,1,1) = '4' then 'SINDH'
			when substr(d.IDNTFTN_VAL,1,1) = '5' then 'BALOCHISTAN'
			when substr(d.IDNTFTN_VAL,1,1) = '7' then 'GILGIT-BALISTAN'
			when substr(d.IDNTFTN_VAL,1,1) = '8' then 'AZAD-KASHMIR'
			ELSE cast(null as varchar(10)) 
			end
			WHEN w.Cust_Type = 'TP' THEN  
			case 
			when substr(W.W_CNIC,1,1) IN ('1', '2') then 'KHYBER-PAKHTUNKHWA'
			when substr(W.W_CNIC,1,1) IN ('3', '6') then 'PUNJAB'
			when substr(W.W_CNIC,1,1) = '4' then 'SINDH'
			when substr(W.W_CNIC,1,1) = '5' then 'BALOCHISTAN'
			when substr(W.W_CNIC,1,1) = '7' then 'GILGIT-BALISTAN'
			when substr(W.W_CNIC,1,1) = '8' then 'AZAD-KASHMIR'
			ELSE cast(null as varchar(10)) 
			end
			END as state,

			CASE WHEN w.Cust_Type = 'AH'  THEN CASE WHEN O.OCPTN_DESC IS NOT NULL OR O.OCPTN_DESC <> '' THEN O.OCPTN_DESC ELSE 'Others' END
			WHEN w.Cust_Type = 'TP' THEN W.w_source_of_funds END AS occupation,
			'PK' as to_country,
			
			DENSE_RANK() OVER(PARTITION BY d.IDNTFTN_VAL ORDER BY d.START_DATE DESC) AS RN
			
			FROM TRXNS T
			INNER JOIN  dp_sdmt_dfdn.WALKIN_TXN W on T.tsactn_id = w.Transaction_ID 
			LEFT JOIN  DP_SDMVW_DFDN.DIM_CUST_VW d ON d.IDNTFTN_VAL = w.w_cnic and d.system_code = 'CBS'
			LEFT JOIN  DP_SDMT_DFDN.DIM_OCPTN_SS O ON O.OCPTN_EDW_ID = D.OCPTN_EDW_ID  and d.system_code = 'CBS'
			LEFT JOIN DP_SDMVW_DFDN.DIM_BRNCH_HIERARCHY_VW B ON T.BRNCH_SROGT_ID = B.BRNCH_SROGT_ID
			WHERE 1=1
			) X
		WHERE 1=1 
		AND X.RN = 1
		AND X.ssn_type NOT IN ('BFN', 'FXP')
		)

		
		, Final_Chunk AS (
		SELECT 
		T.CATEGORY,
		T.CATEGORY_TYPE_DESC,
		TRIM(T.TSACTN_ID) AS transactionnumber,
		B.BRNCH_DESC || ' (' || T.BRNCH_SROGT_ID || ')' AS transaction_location,
		CASE 
		WHEN CR_DR_IND = 'D' THEN 'CHEQUE WITHDRAWAL'  
		WHEN CR_DR_IND = 'C' THEN 'CASH DEPOSIT' 
		END AS transaction_description,
		TO_CHAR(T.TSACTN_DT , 'YYYY-MM-DD') ||  'T00:00:00' as date_transaction,
		B.BRNCH_DESC || ' (' || T.BRNCH_SROGT_ID || ')' AS teller,
		B.CITY_NAME AS authorized,
		'TMBRN' AS transmode_code,
		CASE WHEN T.CURY_EDW_ID = 'PKR' THEN CAST(T.TSACTN_AMT AS INT)
		ELSE CAST(T.FRGN_TSACTN_AMT_PKR AS INT) END AS amount_local,   
	
		CASE 
		WHEN CR_DR_IND = 'D' THEN 'FTCHQ'  
		WHEN CR_DR_IND = 'C' THEN 'FTCAS'
		END AS TFMC_from_funds_code,
		'UBL Bank Limited' AS TFMC_institution_name,
		'43' AS TFMC_institution_code,
		'FALSE' AS TFMC_non_bank_institution,
		BB.BRNCH_DESC || ' (' || T.ACCT_BRNCH_SROGT_ID || ')'  AS TFMC_branch,
		T.ACCT_SROGT_ID AS TFMC_account,
		T.ACCT_CURY_EDW_ID AS TFMC_currency_code,
		T.FRGN_CCY AS TFMC_Foreign_Currency_Code,
		T.FRGN_TSACTN_AMT AS TFMC_Foreign_Amount,
		T.EXCHANGE_RATE AS TFMC_Foreign_Exchange_Rate,
		T.ACCT_DESC AS TFMC_account_name,
		T.ACCT_TYPE_DESC AS TFMC_Acct_Type_Desc,
		T.ACCT_TYPE_CODE AS TFMC_personal_account_type,
		T.ACCT_DESC AS TFMC_name,
		T.CATEGORY_TYPE_CODE AS TFMC_incorporation_legal_form,
		T.CATEGORY_TYPE_DESC AS TFMC_Category_Type_Desc,
		OREPLACE(BUS.BUSINESS_DESC, '"', '') AS TFMC_business,

		case when d.MBL_NUM is not null and d.MBL_NUM <> '' then 'PAPVT' 
				  when d.MBL_NUM is null OR d.MBL_NUM = '' then 'PAOFF' end as TFMC_tph_contact_type,
		case when d.MBL_NUM is not null and d.MBL_NUM <> '' then 'COMOB' else 'COLAN' end as TFMC_tph_communication_type,
		'92' as TFMC_tph_country_prefix,			  
        CASE
			when D.MBL_NUM is not null AND D.MBL_NUM <> ''  
			THEN CASE WHEN REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' ) IS NULL OR REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' ) = ''
						THEN TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') ) ELSE REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' )  END
	        when D.PHN_RSDNC is not null AND D.PHN_RSDNC <> '' then TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.PHN_RSDNC), '[^ ]+', 1, 1), '[^0-9]', '') )
	        else 
			case 
				WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' AND REGEXP_SIMILAR(D.PHN_BUSN, '.*[0-9].*') = '1' THEN CAST(NULL AS VARCHAR(11))
				WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' THEN CAST(NULL AS VARCHAR(11))
				ELSE 
					case
						when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,3) = '092' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3) 
						when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,2) = '92' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3)  
						ELSE trim(LEADING '0' FROM regexp_replace(D.PHN_BUSN, '[^0-9]', ''))
					end
			end 
		END as TFMC_tph_number, 				  

		case when d.PERM_ADDR is not null and d.PERM_ADDR <> '' then 'PAPVT' 
					when d.PERM_ADDR is null OR d.PERM_ADDR = '' then 'PAOFF' end as TFMC_address_type,

	   TRIM(OREPLACE(OREPLACE( 
		CASE 
		WHEN TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is not null AND TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3
		              THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' ')  , '[[:space:]]+', ' '))  
		WHEN (TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
				       AND (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
				      THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' ')) 
		WHEN (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
				       AND ( TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
					   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))
		WHEN (TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3 ) 
				       AND (TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
					   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))		   
		ELSE CAST(NULL AS VARCHAR(10)) 
		END
		,CHR(13),' '),CHR(10), ' ')) as TFMC_address,
		BB.CITY_NAME AS TFMC_city,
		'PK' as TFMC_country_code,
		CASE WHEN BB.PROV_NAME = 'FATA' THEN 'KHYBER-PAKHTUNKHWA'
					WHEN BB.PROV_NAME = 'ISLAMABAD' THEN 'PUNJAB'
					ELSE BB.PROV_NAME 
		END AS TFMC_State,
		'PK' AS TFMC_incorporation_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN 
					CASE 
					 WHEN d.GNDR IS NOT NULL THEN d.GNDR
					 WHEN d.GNDR IS NULL THEN 
								CASE WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'M' 
								WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'F' 
								ELSE CAST(NULL AS VARCHAR(10)) END END
			END
		) AS DIR1_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN 
					CASE 
					 WHEN d.TITL IS NOT NULL THEN d.TITL
					 WHEN d.TITL IS NULL THEN 
								CASE WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'MR' 
								WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'MS'
								ELSE CAST(NULL AS VARCHAR(10)) END END
			END
		) AS DIR1_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z0-9 ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
						FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
			END
		) AS DIR1_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN 
				CASE WHEN  REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0 
							THEN  TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
				              			  POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) )
							ELSE 
									CASE WHEN (D.FRST_NAME IS NULL AND D.MDL_NAME IS NULL AND D.LAST_NAME IS NULL) OR (D.FRST_NAME = '' AND D.MDL_NAME = '' AND D.LAST_NAME = '')
												THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
												 			FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
												ELSE 
														CASE WHEN REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0
																	THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
													            				POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) 
														ELSE TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
																 	FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
														END
									END
				END
			END
		) AS DIR1_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN TO_CHAR(D.DT_OF_BIRTH , 'YYYY-MM-DD') ||  'T00:00:00' 
			END
		) AS DIR1_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.FTHR_NAME, '[^A-Za-z ]', ' '), ' +', ' '))
			END
		) AS DIR1_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN D.IDNTFTN_TYPE_EDW_ID 
			END
		) AS DIR1_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN
							CASE WHEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) = '' THEN CAST(NULL AS VARCHAR(10)) 
											   ELSE TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) END
			END
		) AS DIR1_SSN

		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN D.CTRY_OF_NTLTY
			END
		) AS DIR1_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN 'PK'
			END
		) AS DIR1_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN
						  CASE WHEN D.MBL_NUM is not null AND D.MBL_NUM <> '' then 'PAPVT' when D.MBL_NUM is null OR D.MBL_NUM = '' then 'PAOFF' END
			END
		) AS DIR1_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN
						  CASE WHEN D.MBL_NUM is not null AND D.MBL_NUM <> '' then 'COMOB' else 'COLAN' END
			END
		) AS DIR1_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN '92'
			END
		) AS DIR1_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN 		
			
			CASE when D.MBL_NUM is not null AND D.MBL_NUM <> ''  
			THEN CASE WHEN REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' ) IS NULL OR REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' ) = ''
						THEN TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') ) ELSE REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' )  END
	        when D.PHN_RSDNC is not null AND D.PHN_RSDNC <> '' then TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.PHN_RSDNC), '[^ ]+', 1, 1), '[^0-9]', '') )
	        else case WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' AND REGEXP_SIMILAR(D.PHN_BUSN, '.*[0-9].*') = '1' THEN CAST(NULL AS VARCHAR(11)) WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' THEN CAST(NULL AS VARCHAR(11))
			ELSE case when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,3) = '092' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3) when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,2) = '92' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3)  
			ELSE trim(LEADING '0' FROM regexp_replace(D.PHN_BUSN, '[^0-9]', '')) end end END	
			END
		) AS DIR1_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN
						 CASE WHEN D.PERM_ADDR is not null and D.PERM_ADDR <> '' then 'PAPVT' 
									 WHEN D.PERM_ADDR is null OR D.PERM_ADDR = '' then 'PAOFF' END
			END
		) AS DIR1_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN 
				CASE 
				WHEN TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is not null AND TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3
				              THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' ')  , '[[:space:]]+', ' '))  
				WHEN (TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
						       AND (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
						      THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' ')) 
				WHEN (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
						       AND ( TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))
				WHEN (TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3 ) 
						       AND (TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))		   
				ELSE CAST(NULL AS VARCHAR(10)) 
				END
			END
		) AS DIR1_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CASE WHEN TRIM(D.RSDNTL_CITY) = '0' THEN CAST(NULL AS VARCHAR(10)) ELSE D.RSDNTL_CITY END
			END
		) AS DIR1_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN 'PK'
			END
		) AS DIR1_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN 
						 CASE  
							when substr(D.IDNTFTN_VAL,1,1) IN ('1', '2') then 'KHYBER-PAKHTUNKHWA'
							when substr(D.IDNTFTN_VAL,1,1) IN ('3', '6') then 'PUNJAB'
							when substr(D.IDNTFTN_VAL,1,1) = '4' then 'SINDH'
							when substr(D.IDNTFTN_VAL,1,1) = '5' then 'BALOCHISTAN'
							when substr(D.IDNTFTN_VAL,1,1) = '7' then 'GILGIT-BALISTAN'
							when substr(D.IDNTFTN_VAL,1,1) = '8' then 'AZAD-KASHMIR'
							ELSE cast(null as varchar(10)) 
						END 
			END
		) AS DIR1_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 1  THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 1 THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN  CASE WHEN _DO.OCPTN_DESC IS NOT NULL OR _DO.OCPTN_DESC <> '' THEN _DO.OCPTN_DESC ELSE 'Others' END 
			END
		) AS DIR1_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR1_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_FATHER_NAME

        , MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 2  THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 2 THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR2_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR2_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS DIR3_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 3 THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 3 THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR3_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR3_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 4  THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 4 THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR4_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR4_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 5   THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 5  THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR5_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR5_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_SSN

		, MAX(
			CASE 
			WHEN DD.D_RN = 6  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 6   THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 6  THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR6_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR6_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 7   THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 7  THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR7_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR7_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8  THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8 THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 8   THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 8  THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR8_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR8_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 9  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 9 THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 9 THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR9_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR9_ROLE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10  THEN DD.D_GNDR 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_GNDR
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_GNDR
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10  THEN DD.D_TITL 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_TITL
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_TITL
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10  THEN DD.D_FRST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_FRST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_FIRSTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10  THEN DD.D_LAST_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_LAST_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_LASTNAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10  THEN DD.D_MOTHER_NAME 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_MOTHER_NAME
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10  THEN DD.D_SSN_TYPE 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_SSN_TYPE
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS DIR10_SSN_TYPE

		, MAX(
			CASE 
			WHEN DD.D_RN = 10  THEN DD.D_SSN 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_SSN
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_SSN
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_DT_OF_BIRTH 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10THEN M.M_DT_OF_BIRTH
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL  THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_DATE_OF_BIRTH

		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_nationality1 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_nationality1
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_nationality1
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_Residence 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_Residence
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_Residence
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_tph_contact_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_tph_contact_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_tph_contact_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_tph_communication_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_tph_communication_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_tph_country_prefix 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_tph_country_prefix
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_tph_number 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_tph_number
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_TPH_NUMBER
							
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_address_type 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_address_type
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_address_type
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_address 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_address
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_ADDRESS
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_city 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_city
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_CITY

		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_country_code 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_country_code
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_country_code
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_state 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_state
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_STATE
		
		, MAX(
			CASE 
			WHEN DD.D_RN = 10 THEN DD.D_OCCUPATION 
		    WHEN DD.D_RN IS NULL AND M.M_RN = 10 THEN M.M_OCCUPATION
			WHEN DD.D_RN IS NULL AND M.M_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS DIR10_OCCUPATION
	
		, MAX(
			'ERDIR' 
		) AS DIR10_ROLE
		
		, CASE WHEN TRIM(LEADING '0' FROM REGEXP_REPLACE(D.TAX_NUM, '[^0-9]', '')) = '' THEN NULL 
		ELSE TRIM(LEADING '0' FROM REGEXP_REPLACE(D.TAX_NUM, '[^0-9]', '')) END AS TFMC_TAX_NUM
		
		, MAX('TRUE') AS SIGNATORY1_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 1  THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 1 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND  DD.D_RN IS NULL THEN 
						CASE 
							 WHEN d.GNDR IS NOT NULL THEN d.GNDR
							 WHEN d.GNDR IS NULL THEN 
										CASE WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'M' 
										WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'F' 
										ELSE CAST(NULL AS VARCHAR(10)) END END
			END
		) AS SIGNATORY1_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN 
					CASE 
					 WHEN d.TITL IS NOT NULL THEN d.TITL
					 WHEN d.TITL IS NULL THEN 
								CASE WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('1','3','5','7','9') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13 THEN 'MR' 
								WHEN RIGHT(d.IDNTFTN_VAL,1) IN ('2','4','6','8','0') AND LENGTH(OREPLACE(OREPLACE(d.IDNTFTN_VAL, '-', ''), '/', '')) = 13  THEN 'MS'
								ELSE CAST(NULL AS VARCHAR(10)) END END
			END
		) AS SIGNATORY1_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 1  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN  TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
						FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ''), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
			END
		) AS SIGNATORY1_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 1  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN 
					CASE WHEN  REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0 
								THEN  TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
					              			  POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) )
								ELSE 
										CASE WHEN (D.FRST_NAME IS NULL AND D.MDL_NAME IS NULL AND D.LAST_NAME IS NULL) OR (D.FRST_NAME = '' AND D.MDL_NAME = '' AND D.LAST_NAME = '')
													THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
													 			FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
													ELSE 
															CASE WHEN REGEXP_SIMILAR(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') , '.*\S+\s+\S+.*') >0
																		THEN TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM   
														            				POSITION (' ' IN REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(D.FRST_NAME, '') || ' ' || COALESCE(D.MDL_NAME, '') || ' ' || COALESCE(D.LAST_NAME, ''), '[^A-Za-z ]', ''), ' +', ' ')), '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  + 1) ) 
															ELSE TRIM(SUBSTRING(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') FROM 1 
																	 	FOR POSITION (' ' IN   REGEXP_REPLACE(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.CUST_NAME, '[^A-Za-z ]', ' '), ' +', ' ')) , '^(MR|MRS|MISS|MS|DR)[.]?[ ]*','',1,1,'i') || ' ')  - 1) ) 
															END
										END
					END
			END
		) AS SIGNATORY1_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.FTHR_NAME, '[^A-Za-z ]', ' '), ' +', ' '))
			END
		) AS SIGNATORY1_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN D.IDNTFTN_TYPE_EDW_ID 
			END
		) AS SIGNATORY1_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN 
							CASE WHEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) = '' THEN CAST(NULL AS VARCHAR(10)) 
															   ELSE TRIM(REGEXP_REPLACE(REGEXP_REPLACE(D.IDNTFTN_VAL, '[^A-Za-z0-9 ]', ''), ' +', ' ')) END
			END
		) AS SIGNATORY1_SSN
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN D.CTRY_OF_NTLTY
			END
		) AS SIGNATORY1_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN 'PK'
			END
		) AS SIGNATORY1_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN 
						  CASE WHEN D.MBL_NUM is not null AND D.MBL_NUM <> '' then 'PAPVT' when D.MBL_NUM is null OR D.MBL_NUM = '' then 'PAOFF' END
			END
		) AS SIGNATORY1_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN 
						  CASE WHEN D.MBL_NUM is not null AND D.MBL_NUM <> '' then 'COMOB' else 'COLAN' END
			END
		) AS SIGNATORY1_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN '92'
			END
		) AS SIGNATORY1_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN 
			CASE when D.MBL_NUM is not null AND D.MBL_NUM <> ''  
			THEN CASE WHEN REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' ) IS NULL OR REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' ) = ''
						THEN TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') ) ELSE REGEXP_SUBSTR(REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.MBL_NUM), '[^ ]+', 1, 1), '[^0-9]', '') , '3.*' )  END
	        when D.PHN_RSDNC is not null AND D.PHN_RSDNC <> '' then TRIM(LEADING '0' FROM REGEXP_REPLACE(REGEXP_SUBSTR(TRIM(D.PHN_RSDNC), '[^ ]+', 1, 1), '[^0-9]', '') )
	        else case WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' AND REGEXP_SIMILAR(D.PHN_BUSN, '.*[0-9].*') = '1' THEN CAST(NULL AS VARCHAR(11)) WHEN REGEXP_SIMILAR(D.PHN_BUSN, '.*[A-Za-z].*') = '1' THEN CAST(NULL AS VARCHAR(11))
			ELSE case when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,3) = '092' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3) when substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 1,2) = '92' then substr(regexp_replace(D.PHN_BUSN, '[^0-9]', ''), 3)  
			ELSE trim(LEADING '0' FROM regexp_replace(D.PHN_BUSN, '[^0-9]', '')) end end END	
			END
		) AS SIGNATORY1_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN TO_CHAR(D.DT_OF_BIRTH , 'YYYY-MM-DD') ||  'T00:00:00'
			END
		) AS SIGNATORY1_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CASE WHEN D.PERM_ADDR is not null and D.PERM_ADDR <> '' then 'PAPVT'  WHEN D.PERM_ADDR is null OR D.PERM_ADDR = '' then 'PAOFF' END
			END
		) AS SIGNATORY1_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN
			CASE 
				WHEN TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is not null AND TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3
				              THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' ')  , '[[:space:]]+', ' '))  
				WHEN (TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.PERM_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
						       AND (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
						      THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.BUSN_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' ')) 
				WHEN (TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.BUSN_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3) 
						       AND ( TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.MLG_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))
				WHEN (TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  is null OR TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))  = '' OR LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.MLG_ADDR), '[^A-Za-z0-9 ]', ' '))) <= 3 ) 
						       AND (TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) is not null AND TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ')) <> '' AND LENGTH(TRIM(REGEXP_REPLACE(TRIM(d.OTH_ADDR), '[^A-Za-z0-9 ]', ' '))) > 3)
							   THEN TRIM(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(d.OTH_ADDR ), '[^A-Za-z0-9 ]', ' ') , '[[:space:]]+', ' '))		   
				ELSE CAST(NULL AS VARCHAR(10)) 
				END
			END
		) AS SIGNATORY1_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CASE WHEN TRIM(D.RSDNTL_CITY) = '0' THEN CAST(NULL AS VARCHAR(10)) ELSE D.RSDNTL_CITY END
			END
		) AS SIGNATORY1_CITY
	
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN 'PK'
			END
		) AS SIGNATORY1_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN 
						  CASE  
							when substr(D.IDNTFTN_VAL,1,1) IN ('1', '2') then 'KHYBER-PAKHTUNKHWA'
							when substr(D.IDNTFTN_VAL,1,1) IN ('3', '6') then 'PUNJAB'
							when substr(D.IDNTFTN_VAL,1,1) = '4' then 'SINDH'
							when substr(D.IDNTFTN_VAL,1,1) = '5' then 'BALOCHISTAN'
							when substr(D.IDNTFTN_VAL,1,1) = '7' then 'GILGIT-BALISTAN'
							when substr(D.IDNTFTN_VAL,1,1) = '8' then 'AZAD-KASHMIR'
							ELSE cast(null as varchar(10)) 
						END
			END
		) AS SIGNATORY1_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 1  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 1 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CASE WHEN _DO.OCPTN_DESC IS NOT NULL OR _DO.OCPTN_DESC <> '' THEN _DO.OCPTN_DESC ELSE 'Others' END 
			END
		) AS SIGNATORY1_OCCUPATION
		
		, MAX(
			'ARPYS' 
		) AS SIGNATORY1_ROLE
		
		-----------------------------------------------------------------------------------------------------------------------------------------------------------
		, MAX('TRUE') AS SIGNATORY2_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 2 THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 2 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2 THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 2  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY2_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 2  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY2_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY2_SSN
		
		 , MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_CITY
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 2 THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 2  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 2 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY2_OCCUPATION
		
		, MAX(
			'ARPYS'
		) AS SIGNATORY2_ROLE
		 
		, MAX('TRUE') AS SIGNATORY3_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 3 THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 3 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3 THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 3  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY3_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 3  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY3_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY3_SSN
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_CITY
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 3 THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 3  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 3 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY3_OCCUPATION
		
		, MAX(
			'ARPYS'
		) AS SIGNATORY3_ROLE
		
		, MAX('TRUE') AS SIGNATORY4_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 4 THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 4 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4 THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 4  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY4_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 4  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY4_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY4_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY4_SSN
		
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_CITY
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 4 THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 4  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 4 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY4_OCCUPATION
		
		, MAX(
			'ARPYS'
		) AS SIGNATORY4_ROLE
		
		, MAX('TRUE') AS SIGNATORY5_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 5 THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 5 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5 THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 5  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY5_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 5  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY5_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY5_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY5_SSN
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_CITY
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 5 THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 5  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 5 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY5_OCCUPATION
		
		, MAX(
			'ARPYS'
		) AS SIGNATORY5_ROLE
		
		, MAX('TRUE') AS SIGNATORY6_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 6 THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 6 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6 THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 6  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY6_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 6  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY6_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY6_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY6_SSN
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_CITY
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 6 THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 6  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 6 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY6_OCCUPATION
		
		, MAX(
			'ARPYS'
		) AS SIGNATORY6_ROLE
		
		, MAX('TRUE') AS SIGNATORY7_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 7 THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 7 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7 THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 7  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY7_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 7  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY7_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY7_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY7_SSN
		
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_CITY
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 7 THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 7  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 7 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY7_OCCUPATION
		
		, MAX(
			'ARPYS'
		) AS SIGNATORY7_ROLE
		
		, MAX('TRUE') AS SIGNATORY8_IS_PRIMARY
		
		, MAX(
			CASE 
				WHEN M.M_RN = 8 THEN M.M_GNDR 
			    WHEN M.M_RN  IS NULL AND DD.D_RN = 8 THEN DD.D_GNDR 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_GNDR
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8 THEN M.M_TITL  
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_TITL
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_TITL
		
		, MAX(
			CASE 
				WHEN M.M_RN = 8  THEN M.M_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_FRST_NAME 
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY8_FIRSTNAME
		
		, MAX(
			CASE 
				WHEN M.M_RN = 8  THEN M.M_LAST_NAME 
			    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_LAST_NAME
				WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_LASTNAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_MOTHER_NAME 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_MOTHER_NAME
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY8_FATHER_NAME
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_SSN_TYPE 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_SSN_TYPE 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY8_SSN_TYPE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_SSN 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_SSN
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL   THEN CAST(NULL AS VARCHAR(50))
			END
		) AS SIGNATORY8_SSN
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_nationality1 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_nationality1 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_nationality1
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_Residence
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_Residence 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_Residence
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_tph_contact_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_tph_contact_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_tph_contact_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_tph_communication_type
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_tph_communication_type 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_tph_communication_type 
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_tph_country_prefix
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_tph_country_prefix
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_tph_country_prefix
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_tph_number 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_tph_number
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_TPH_NUMBER
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_DT_OF_BIRTH 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_DT_OF_BIRTH
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_DATE_OF_BIRTH
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_address_type 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_address_type
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_address_type
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_address 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_address
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_ADDRESS
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_city
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_city 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_CITY
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_country_code
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_country_code 
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_country_code

		, MAX(
			CASE 
			WHEN M.M_RN = 8 THEN M.M_state
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_state  
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_STATE
		
		, MAX(
			CASE 
			WHEN M.M_RN = 8  THEN M.M_OCCUPATION 
		    WHEN M.M_RN IS NULL AND DD.D_RN = 8 THEN DD.D_OCCUPATION
			WHEN M.M_RN IS NULL AND DD.D_RN IS NULL THEN CAST(NULL AS VARCHAR(50)) 
			END
		) AS SIGNATORY8_OCCUPATION
		
		, MAX(
			'ARPYS'
		) AS SIGNATORY8_ROLE
		
		, TO_CHAR(T.ACCT_ORIGNL_OPN_DT , 'YYYY-MM-DD') ||  'T00:00:00' AS TFMC_open,
		'ASACT' as TFMC_status_code,
		-- d.CTRY_OF_NTLTY as TFMC_to_country
		'PK' AS TFMC_from_country,
		
		CASE 
		WHEN CR_DR_IND = 'D' THEN 'FTCAS'
		WHEN CR_DR_IND = 'C' THEN 'FTDEP' 
		END AS TTMC_to_funds_code,
		W.Gender AS TTMC_Gender,
		W."Title" AS TTMC_Title,
		W.First_Name AS TTMC_First_Name,
		W.Last_Name AS TTMC_Last_Name,
		W.Birth_Date AS TTMC_Birth_Date,
		W.Mother_Name AS TTMC_Mother_Name,
		W.ssn_type AS TTMC_ssn_type,
		W.ssn AS TTMC_ssn,
		W.nationality1 AS TTMC_nationality1,
		W.Residence AS TTMC_Residence,
		W.tph_contact_type AS TTMC_tph_contact_type,
		W.tph_communication_type AS TTMC_tph_communication_type,
		W.tph_country_prefix AS TTMC_tph_country_prefix,
		W.tph_number AS TTMC_tph_number,
		W.address_type AS TTMC_address_type,
		W.address AS TTMC_address,
		W.city AS TTMC_city,
		W.country_code AS TTMC_country_code,
		W.state AS TTMC_state,
		W.occupation AS TTMC_occupation,
		W.to_country AS TTMC_to_country

		FROM TRXNS T
		LEFT JOIN DP_SDMVW_DFDN.DIM_CUST_VW d ON d.CUST_SROGT_ID = T.CUST_SROGT_ID and d.system_code = 'CBS'
		LEFT JOIN DP_SDMT_DFDN.DIM_OCPTN_SS _DO ON D.OCPTN_EDW_ID = _DO.OCPTN_EDW_ID
		LEFT JOIN DP_WRK_CBS.FM_CLIENT_DAILY fmd ON fmd.client_no = T.CUST_SROGT_ID
		LEFT JOIN DP_SDMVW_DFDN.DIM_BUSINESS_VW BUS ON fmd.business = bus.BUSINESS
		LEFT JOIN DP_SDMVW_DFDN.DIM_CUST_TYPE_VW CTY ON D.CUST_TYPE_EDW_ID = CTY.CUST_TYPE_EDW_ID
		LEFT JOIN DP_SDMVW_DFDN.DIM_BRNCH_HIERARCHY_VW B ON T.BRNCH_SROGT_ID = B.BRNCH_SROGT_ID
		LEFT JOIN DP_SDMVW_DFDN.DIM_BRNCH_HIERARCHY_VW BB ON T.ACCT_BRNCH_SROGT_ID = BB.BRNCH_SROGT_ID 
		LEFT JOIN MANDATE M ON M.ACCT_SROGT_ID = T.ACCT_SROGT_ID
		LEFT JOIN DIRECTORS DD ON DD.CUST_SROGT_ID = T.CUST_SROGT_ID 
		LEFT JOIN WALKIN_DETAILS W ON W.Transaction_ID = T.TSACTN_ID
		WHERE 1=1 
		GROUP BY 
		CATEGORY,CATEGORY_TYPE_DESC,transactionnumber,transaction_location,transaction_description,date_transaction,teller,authorized,transmode_code,amount_local,
		TFMC_from_funds_code,TFMC_institution_name,TFMC_institution_code,TFMC_non_bank_institution,TFMC_branch,TFMC_account,TFMC_currency_code,
		TFMC_Foreign_Currency_Code, TFMC_Foreign_Amount, TFMC_Foreign_Exchange_Rate, TFMC_account_name,TFMC_Acct_Type_Desc,TFMC_personal_account_type,TFMC_name,TFMC_incorporation_legal_form, TFMC_Category_Type_Desc,
		TFMC_business,TFMC_tph_contact_type,TFMC_tph_communication_type, TFMC_tph_country_prefix,TFMC_tph_number,TFMC_address_type,TFMC_address,TFMC_city,TFMC_country_code,
		TFMC_state,TFMC_incorporation_country_code,TFMC_TAX_NUM, TFMC_open,TFMC_status_code,TFMC_from_country ,
		
		TTMC_to_funds_code,TTMC_Gender,TTMC_Title,TTMC_First_Name,TTMC_Last_Name,TTMC_Birth_Date,TTMC_Mother_Name,TTMC_ssn_type,TTMC_ssn,TTMC_nationality1,TTMC_Residence,
		TTMC_tph_contact_type,TTMC_tph_communication_type,TTMC_tph_country_prefix,TTMC_tph_number,TTMC_address_type,TTMC_address,TTMC_city,TTMC_country_code,TTMC_state,TTMC_occupation,TTMC_to_country
		)
		
		, DATA_V1 AS (
		
		SELECT 
		CAST(CATEGORY AS VARCHAR(20)) AS CATEGORY , 
	    CAST(CATEGORY_TYPE_DESC AS VARCHAR(99)) AS CATEGORY_TYPE_DESC ,
		CAST(transactionnumber AS BIGINT) AS transactionnumber,
		CAST(transaction_location AS VARCHAR(99)) AS transaction_location,
		CAST(transaction_description AS VARCHAR(99)) AS transaction_description,
		CAST(date_transaction AS VARCHAR(20)) AS date_transaction,
		CAST(teller AS VARCHAR(99)) AS teller ,
		CAST(authorized AS VARCHAR(99)) AS authorized,
		CAST(transmode_code AS VARCHAR(10)) AS transmode_code,
		CAST(amount_local AS INT) AS amount_local,
		--------------------------------------- FROM MY CLEINT TAG -----------------------------------------------------------
		CAST(TFMC_from_funds_code AS VARCHAR(20)) AS TFMC_from_funds_code,
		CAST(TFMC_institution_name AS VARCHAR(99)) AS TFMC_institution_name,
		CAST(TFMC_institution_code AS VARCHAR(99)) AS TFMC_institution_code,
		CAST(TFMC_non_bank_institution AS VARCHAR(99)) AS TFMC_non_bank_institution,
		CAST(TFMC_branch AS VARCHAR(99)) AS TFMC_branch,
		CAST(TFMC_account AS VARCHAR(20)) AS TFMC_account,
		CAST(TFMC_currency_code AS VARCHAR(10)) AS TFMC_currency_code,
		CAST(TFMC_Foreign_Currency_Code AS VARCHAR(10)) AS TFMC_Foreign_Currency_Code,
		CAST(TFMC_Foreign_Amount AS INT) AS TFMC_Foreign_Amount  ,
		CAST(TFMC_Foreign_Exchange_Rate AS DECIMAL(38,4)) AS TFMC_Foreign_Exchange_Rate,
		CAST(TFMC_account_name AS VARCHAR(99)) AS TFMC_account_name, 
		CAST(TFMC_personal_account_type AS VARCHAR(20)) AS TFMC_personal_account_type, 
		CAST(TFMC_name AS VARCHAR(99)) AS TFMC_name, 
		CAST(TFMC_incorporation_legal_form AS VARCHAR(20)) AS TFMC_incorporation_legal_form, 
		CAST(TFMC_business AS VARCHAR(99)) AS TFMC_business, 
		CAST(TFMC_tph_contact_type AS VARCHAR(20)) AS TFMC_tph_contact_type, 
		CAST(TFMC_tph_communication_type AS VARCHAR(20)) AS TFMC_tph_communication_type, 
		CAST(TFMC_tph_country_prefix AS VARCHAR(10)) AS TFMC_tph_country_prefix ,
		CAST(CASE WHEN TFMC_tph_number IS NULL OR TFMC_tph_number = '' THEN COALESCE(SIGNATORY1_TPH_NUMBER, DIR1_TPH_NUMBER) ELSE TFMC_tph_number END AS VARCHAR(20)) AS TFMC_tph_number,
		CAST(TFMC_address_type AS VARCHAR(10)) AS TFMC_address_type,
		CAST(CASE WHEN TFMC_address IS NULL OR TFMC_address = '' THEN COALESCE(SIGNATORY1_ADDRESS, DIR1_ADDRESS) ELSE TFMC_address END AS VARCHAR(99)) AS TFMC_address,
		CAST(TFMC_city AS VARCHAR(50)) AS TFMC_city,
		CAST(TFMC_country_code AS VARCHAR(10)) AS TFMC_country_code,
		CAST(TFMC_state AS VARCHAR(50)) AS TFMC_state,
		CAST(TFMC_incorporation_country_code AS VARCHAR(20)) AS TFMC_incorporation_country_code,
		------------------------------------- DIRECTOR 1 -----------------------------------------
		CAST(DIR1_GNDR AS VARCHAR(10)) AS DIR1_GNDR,
		CAST(DIR1_TITL AS VARCHAR(10)) AS DIR1_TITL,
		CAST(DIR1_FIRSTNAME AS VARCHAR(99)) AS DIR1_FIRSTNAME,
		CAST(DIR1_LASTNAME AS VARCHAR(99)) AS DIR1_LASTNAME,
		CAST(DIR1_FATHER_NAME AS VARCHAR(99)) AS DIR1_FATHER_NAME,
		CAST(DIR1_SSN_TYPE AS VARCHAR(10)) AS DIR1_SSN_TYPE,
		CAST(CASE WHEN DIR1_SSN_TYPE IN ('NIC', 'PPT','POC') THEN DIR1_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR1_SSN,
	    CAST(DIR1_nationality1 AS VARCHAR(10)) AS DIR1_nationality1,
	    CAST(DIR1_Residence AS VARCHAR(10)) AS DIR1_Residence,
	    CAST(DIR1_tph_contact_type AS VARCHAR(10)) AS DIR1_tph_contact_type,
	    CAST(DIR1_tph_communication_type AS VARCHAR(10)) AS DIR1_tph_communication_type,
	    CAST(DIR1_tph_country_prefix AS VARCHAR(10)) AS DIR1_tph_country_prefix,
		CAST(CASE WHEN DIR1_TPH_NUMBER IS NULL OR DIR1_TPH_NUMBER = '' THEN 
					COALESCE(CASE WHEN SIGNATORY1_TPH_NUMBER IS NULL OR SIGNATORY1_TPH_NUMBER = '' THEN TTMC_tph_number END, SIGNATORY1_TPH_NUMBER ) ELSE DIR1_TPH_NUMBER END AS VARCHAR(50)) AS DIR1_TPH_NUMBER,
		CAST(CASE WHEN DIR1_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR1_DATE_OF_BIRTH, 3) ELSE DIR1_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR1_DATE_OF_BIRTH,
	    CAST(DIR1_address_type AS VARCHAR(10)) AS DIR1_address_type,
		CAST(DIR1_ADDRESS AS VARCHAR(99)) AS DIR1_ADDRESS,
	    CAST(DIR1_CITY AS VARCHAR(20)) AS DIR1_CITY,
	    CAST(DIR1_country_code AS VARCHAR(10)) AS DIR1_country_code,
	    CAST(DIR1_STATE AS VARCHAR(20)) AS DIR1_STATE,
		CAST(DIR1_OCCUPATION AS VARCHAR(99)) AS DIR1_OCCUPATION,
	    CAST(DIR1_ROLE AS VARCHAR(10)) AS DIR1_ROLE,
		------------------------------------- DIRECTOR 2 -----------------------------------------
		CAST(DIR2_GNDR AS VARCHAR(10)) AS DIR2_GNDR,
		CAST(DIR2_TITL AS VARCHAR(10)) AS DIR2_TITL,
		CAST(DIR2_FIRSTNAME AS VARCHAR(99)) AS DIR2_FIRSTNAME,
		CAST(DIR2_LASTNAME AS VARCHAR(99)) AS DIR2_LASTNAME,
		CAST(DIR2_FATHER_NAME AS VARCHAR(99)) AS DIR2_FATHER_NAME,
		CAST(DIR2_SSN_TYPE AS VARCHAR(10)) AS DIR2_SSN_TYPE,
		CAST(CASE WHEN DIR2_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR2_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR2_SSN,
	    CAST(DIR2_nationality1 AS VARCHAR(10)) AS DIR2_nationality1,
	    CAST(DIR2_Residence AS VARCHAR(10)) AS DIR2_Residence,
	    CAST(DIR2_tph_contact_type AS VARCHAR(10)) AS DIR2_tph_contact_type,
	    CAST(DIR2_tph_communication_type AS VARCHAR(10)) AS DIR2_tph_communication_type,
	    CAST(DIR2_tph_country_prefix AS VARCHAR(10)) AS DIR2_tph_country_prefix,
		CAST(DIR2_TPH_NUMBER AS VARCHAR(20)) AS DIR2_TPH_NUMBER,
		CAST(CASE WHEN DIR2_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR2_DATE_OF_BIRTH, 3) ELSE DIR2_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR2_DATE_OF_BIRTH,
	    CAST(DIR2_address_type AS VARCHAR(10)) AS DIR2_address_type,
		CAST(DIR2_ADDRESS AS VARCHAR(99)) AS DIR2_ADDRESS,
	    CAST(DIR2_CITY AS VARCHAR(20)) AS DIR2_CITY,
	    CAST(DIR2_country_code AS VARCHAR(10)) AS DIR2_country_code,
	    CAST(DIR2_STATE AS VARCHAR(20)) AS DIR2_STATE,
		CAST(DIR2_OCCUPATION AS VARCHAR(99)) AS DIR2_OCCUPATION,
	    CAST(CASE WHEN DIR2_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR2_ROLE END AS VARCHAR(10)) AS DIR2_ROLE,
		------------------------------------- DIRECTOR 3 -----------------------------------------
		CAST(DIR3_GNDR AS VARCHAR(10)) AS DIR3_GNDR,
		CAST(DIR3_TITL AS VARCHAR(10)) AS DIR3_TITL,
		CAST(DIR3_FIRSTNAME AS VARCHAR(99)) AS DIR3_FIRSTNAME,
		CAST(DIR3_LASTNAME AS VARCHAR(99)) AS DIR3_LASTNAME,
		CAST(DIR3_FATHER_NAME AS VARCHAR(99)) AS DIR3_FATHER_NAME,
		CAST(DIR3_SSN_TYPE AS VARCHAR(10)) AS DIR3_SSN_TYPE,
		CAST(CASE WHEN DIR3_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR3_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR3_SSN,
	    CAST(DIR3_nationality1 AS VARCHAR(10)) AS DIR3_nationality1,
	    CAST(DIR3_Residence AS VARCHAR(10)) AS DIR3_Residence,
	    CAST(DIR3_tph_contact_type AS VARCHAR(10)) AS DIR3_tph_contact_type,
	    CAST(DIR3_tph_communication_type AS VARCHAR(10)) AS DIR3_tph_communication_type,
	    CAST(DIR3_tph_country_prefix AS VARCHAR(10)) AS DIR3_tph_country_prefix,
		CAST(DIR3_TPH_NUMBER AS VARCHAR(20)) AS DIR3_TPH_NUMBER,
		CAST(CASE WHEN DIR3_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR3_DATE_OF_BIRTH, 3) ELSE DIR3_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR3_DATE_OF_BIRTH,
	    CAST(DIR3_address_type AS VARCHAR(10)) AS DIR3_address_type,
		CAST(DIR3_ADDRESS AS VARCHAR(99)) AS DIR3_ADDRESS,
	    CAST(DIR3_CITY AS VARCHAR(20)) AS DIR3_CITY,
	    CAST(DIR3_country_code AS VARCHAR(10)) AS DIR3_country_code,
	    CAST(DIR3_STATE AS VARCHAR(20)) AS DIR3_STATE,
		CAST(DIR3_OCCUPATION AS VARCHAR(99)) AS DIR3_OCCUPATION,
	    CAST(CASE WHEN DIR3_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR3_ROLE END AS VARCHAR(10)) AS DIR3_ROLE,
		------------------------------------- DIRECTOR 4 -----------------------------------------
		CAST(DIR4_GNDR AS VARCHAR(10)) AS DIR4_GNDR,
		CAST(DIR4_TITL AS VARCHAR(10)) AS DIR4_TITL,
		CAST(DIR4_FIRSTNAME AS VARCHAR(99)) AS DIR4_FIRSTNAME,
		CAST(DIR4_LASTNAME AS VARCHAR(99)) AS DIR4_LASTNAME,
		CAST(DIR4_FATHER_NAME AS VARCHAR(99)) AS DIR4_FATHER_NAME,
		CAST(DIR4_SSN_TYPE AS VARCHAR(10)) AS DIR4_SSN_TYPE,
		CAST(CASE WHEN DIR4_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR4_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR4_SSN,
	    CAST(DIR4_nationality1 AS VARCHAR(10)) AS DIR4_nationality1,
	    CAST(DIR4_Residence AS VARCHAR(10)) AS DIR4_Residence,
	    CAST(DIR4_tph_contact_type AS VARCHAR(10)) AS DIR4_tph_contact_type,
	    CAST(DIR4_tph_communication_type AS VARCHAR(10)) AS DIR4_tph_communication_type,
	    CAST(DIR4_tph_country_prefix AS VARCHAR(10)) AS DIR4_tph_country_prefix,
		CAST(DIR4_TPH_NUMBER AS VARCHAR(20)) AS DIR4_TPH_NUMBER,
		CAST(CASE WHEN DIR4_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR4_DATE_OF_BIRTH, 3) ELSE DIR4_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR4_DATE_OF_BIRTH,
	    CAST(DIR4_address_type AS VARCHAR(10)) AS DIR4_address_type,
		CAST(DIR4_ADDRESS AS VARCHAR(99)) AS DIR4_ADDRESS,
	    CAST(DIR4_CITY AS VARCHAR(20)) AS DIR4_CITY,
	    CAST(DIR4_country_code AS VARCHAR(10)) AS DIR4_country_code,
	    CAST(DIR4_STATE AS VARCHAR(20)) AS DIR4_STATE,
		CAST(DIR4_OCCUPATION AS VARCHAR(99)) AS DIR4_OCCUPATION,
	    CAST(CASE WHEN DIR4_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR4_ROLE END AS VARCHAR(10)) AS DIR4_ROLE,
		------------------------------------- DIRECTOR 5 -----------------------------------------
		CAST(DIR5_GNDR AS VARCHAR(10)) AS DIR5_GNDR,
		CAST(DIR5_TITL AS VARCHAR(10)) AS DIR5_TITL,
		CAST(DIR5_FIRSTNAME AS VARCHAR(99)) AS DIR5_FIRSTNAME,
		CAST(DIR5_LASTNAME AS VARCHAR(99)) AS DIR5_LASTNAME,
		CAST(DIR5_FATHER_NAME AS VARCHAR(99)) AS DIR5_FATHER_NAME,
		CAST(DIR5_SSN_TYPE AS VARCHAR(10)) AS DIR5_SSN_TYPE,
		CAST(CASE WHEN DIR5_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR5_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR5_SSN,
	    CAST(DIR5_nationality1 AS VARCHAR(10)) AS DIR5_nationality1,
	    CAST(DIR5_Residence AS VARCHAR(10)) AS DIR5_Residence,
	    CAST(DIR5_tph_contact_type AS VARCHAR(10)) AS DIR5_tph_contact_type,
	    CAST(DIR5_tph_communication_type AS VARCHAR(10)) AS DIR5_tph_communication_type,
	    CAST(DIR5_tph_country_prefix AS VARCHAR(10)) AS DIR5_tph_country_prefix,
		CAST(DIR5_TPH_NUMBER AS VARCHAR(20)) AS DIR5_TPH_NUMBER,
		CAST(CASE WHEN DIR5_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR5_DATE_OF_BIRTH, 3) ELSE DIR5_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR5_DATE_OF_BIRTH,
	    CAST(DIR5_address_type AS VARCHAR(10)) AS DIR5_address_type,
		CAST(DIR5_ADDRESS AS VARCHAR(99)) AS DIR5_ADDRESS,
	    CAST(DIR5_CITY AS VARCHAR(20)) AS DIR5_CITY,
	    CAST(DIR5_country_code AS VARCHAR(10)) AS DIR5_country_code,
	    CAST(DIR5_STATE AS VARCHAR(20)) AS DIR5_STATE,
		CAST(DIR5_OCCUPATION AS VARCHAR(99)) AS DIR5_OCCUPATION,
	    CAST(CASE WHEN DIR5_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR5_ROLE END AS VARCHAR(10)) AS DIR5_ROLE,
		------------------------------------- DIRECTOR 6 -----------------------------------------
		CAST(DIR6_GNDR AS VARCHAR(10)) AS DIR6_GNDR,
		CAST(DIR6_TITL AS VARCHAR(10)) AS DIR6_TITL,
		CAST(DIR6_FIRSTNAME AS VARCHAR(99)) AS DIR6_FIRSTNAME,
		CAST(DIR6_LASTNAME AS VARCHAR(99)) AS DIR6_LASTNAME,
		CAST(DIR6_FATHER_NAME AS VARCHAR(99)) AS DIR6_FATHER_NAME,
		CAST(DIR6_SSN_TYPE AS VARCHAR(10)) AS DIR6_SSN_TYPE,
		CAST(CASE WHEN DIR6_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR6_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR6_SSN,
	    CAST(DIR6_nationality1 AS VARCHAR(10)) AS DIR6_nationality1,
	    CAST(DIR6_Residence AS VARCHAR(10)) AS DIR6_Residence,
	    CAST(DIR6_tph_contact_type AS VARCHAR(10)) AS DIR6_tph_contact_type,
	    CAST(DIR6_tph_communication_type AS VARCHAR(10)) AS DIR6_tph_communication_type,
	    CAST(DIR6_tph_country_prefix AS VARCHAR(10)) AS DIR6_tph_country_prefix,
		CAST(DIR6_TPH_NUMBER AS VARCHAR(20)) AS DIR6_TPH_NUMBER,
		CAST(CASE WHEN DIR6_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR6_DATE_OF_BIRTH, 3) ELSE DIR6_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR6_DATE_OF_BIRTH,
	    CAST(DIR6_address_type AS VARCHAR(10)) AS DIR6_address_type,
		CAST(DIR6_ADDRESS AS VARCHAR(99)) AS DIR6_ADDRESS,
	    CAST(DIR6_CITY AS VARCHAR(20)) AS DIR6_CITY,
	    CAST(DIR6_country_code AS VARCHAR(10)) AS DIR6_country_code,
	    CAST(DIR6_STATE AS VARCHAR(20)) AS DIR6_STATE,
		CAST(DIR6_OCCUPATION AS VARCHAR(99)) AS DIR6_OCCUPATION,
	    CAST(CASE WHEN DIR6_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR6_ROLE END AS VARCHAR(10)) AS DIR6_ROLE,
		------------------------------------- DIRECTOR 7 -----------------------------------------
		CAST(DIR7_GNDR AS VARCHAR(10)) AS DIR7_GNDR,
		CAST(DIR7_TITL AS VARCHAR(10)) AS DIR7_TITL,
		CAST(DIR7_FIRSTNAME AS VARCHAR(99)) AS DIR7_FIRSTNAME,
		CAST(DIR7_LASTNAME AS VARCHAR(99)) AS DIR7_LASTNAME,
		CAST(DIR7_FATHER_NAME AS VARCHAR(99)) AS DIR7_FATHER_NAME,
		CAST(DIR7_SSN_TYPE AS VARCHAR(10)) AS DIR7_SSN_TYPE,
		CAST(CASE WHEN DIR7_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR7_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR7_SSN,
	    CAST(DIR7_nationality1 AS VARCHAR(10)) AS DIR7_nationality1,
	    CAST(DIR7_Residence AS VARCHAR(10)) AS DIR7_Residence,
	    CAST(DIR7_tph_contact_type AS VARCHAR(10)) AS DIR7_tph_contact_type,
	    CAST(DIR7_tph_communication_type AS VARCHAR(10)) AS DIR7_tph_communication_type,
	    CAST(DIR7_tph_country_prefix AS VARCHAR(10)) AS DIR7_tph_country_prefix,
		CAST(DIR7_TPH_NUMBER AS VARCHAR(20)) AS DIR7_TPH_NUMBER,
		CAST(CASE WHEN DIR7_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR7_DATE_OF_BIRTH, 3) ELSE DIR7_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR7_DATE_OF_BIRTH,
	    CAST(DIR7_address_type AS VARCHAR(10)) AS DIR7_address_type,
		CAST(DIR7_ADDRESS AS VARCHAR(99)) AS DIR7_ADDRESS,
	    CAST(DIR7_CITY AS VARCHAR(20)) AS DIR7_CITY,
	    CAST(DIR7_country_code AS VARCHAR(10)) AS DIR7_country_code,
	    CAST(DIR7_STATE AS VARCHAR(20)) AS DIR7_STATE,
		CAST(DIR7_OCCUPATION AS VARCHAR(99)) AS DIR7_OCCUPATION,
	    CAST(CASE WHEN DIR7_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR7_ROLE END AS VARCHAR(10)) AS DIR7_ROLE,
		------------------------------------- DIRECTOR 8 -----------------------------------------
		CAST(DIR8_GNDR AS VARCHAR(10)) AS DIR8_GNDR,
		CAST(DIR8_TITL AS VARCHAR(10)) AS DIR8_TITL,
		CAST(DIR8_FIRSTNAME AS VARCHAR(99)) AS DIR8_FIRSTNAME,
		CAST(DIR8_LASTNAME AS VARCHAR(99)) AS DIR8_LASTNAME,
		CAST(DIR8_FATHER_NAME AS VARCHAR(99)) AS DIR8_FATHER_NAME,
		CAST(DIR8_SSN_TYPE AS VARCHAR(10)) AS DIR8_SSN_TYPE,
		CAST(CASE WHEN DIR8_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR8_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR8_SSN,
	    CAST(DIR8_nationality1 AS VARCHAR(10)) AS DIR8_nationality1,
	    CAST(DIR8_Residence AS VARCHAR(10)) AS DIR8_Residence,
	    CAST(DIR8_tph_contact_type AS VARCHAR(10)) AS DIR8_tph_contact_type,
	    CAST(DIR8_tph_communication_type AS VARCHAR(10)) AS DIR8_tph_communication_type,
	    CAST(DIR8_tph_country_prefix AS VARCHAR(10)) AS DIR8_tph_country_prefix,
		CAST(DIR8_TPH_NUMBER AS VARCHAR(20)) AS DIR8_TPH_NUMBER,
		CAST(CASE WHEN DIR8_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR8_DATE_OF_BIRTH, 3) ELSE DIR8_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR8_DATE_OF_BIRTH,
	    CAST(DIR8_address_type AS VARCHAR(10)) AS DIR8_address_type,
		CAST(DIR8_ADDRESS AS VARCHAR(99)) AS DIR8_ADDRESS,
	    CAST(DIR8_CITY AS VARCHAR(20)) AS DIR8_CITY,
	    CAST(DIR8_country_code AS VARCHAR(10)) AS DIR8_country_code,
	    CAST(DIR8_STATE AS VARCHAR(20)) AS DIR8_STATE,
		CAST(DIR8_OCCUPATION AS VARCHAR(99)) AS DIR8_OCCUPATION,
	    CAST(CASE WHEN DIR8_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR8_ROLE END AS VARCHAR(10)) AS DIR8_ROLE,
		------------------------------------- DIRECTOR 9 -----------------------------------------
		CAST(DIR9_GNDR AS VARCHAR(10)) AS DIR9_GNDR,
		CAST(DIR9_TITL AS VARCHAR(10)) AS DIR9_TITL,
		CAST(DIR9_FIRSTNAME AS VARCHAR(99)) AS DIR9_FIRSTNAME,
		CAST(DIR9_LASTNAME AS VARCHAR(99)) AS DIR9_LASTNAME,
		CAST(DIR9_FATHER_NAME AS VARCHAR(99)) AS DIR9_FATHER_NAME,
		CAST(DIR9_SSN_TYPE AS VARCHAR(10)) AS DIR9_SSN_TYPE,
		CAST(CASE WHEN DIR9_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR9_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR9_SSN,
	    CAST(DIR9_nationality1 AS VARCHAR(10)) AS DIR9_nationality1,
	    CAST(DIR9_Residence AS VARCHAR(10)) AS DIR9_Residence,
	    CAST(DIR9_tph_contact_type AS VARCHAR(10)) AS DIR9_tph_contact_type,
	    CAST(DIR9_tph_communication_type AS VARCHAR(10)) AS DIR9_tph_communication_type,
	    CAST(DIR9_tph_country_prefix AS VARCHAR(10)) AS DIR9_tph_country_prefix,
		CAST(DIR9_TPH_NUMBER AS VARCHAR(20)) AS DIR9_TPH_NUMBER,
		CAST(CASE WHEN DIR9_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR9_DATE_OF_BIRTH, 3) ELSE DIR9_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR9_DATE_OF_BIRTH,
	    CAST(DIR9_address_type AS VARCHAR(10)) AS DIR9_address_type,
		CAST(DIR9_ADDRESS AS VARCHAR(99)) AS DIR9_ADDRESS,
	    CAST(DIR9_CITY AS VARCHAR(20)) AS DIR9_CITY,
	    CAST(DIR9_country_code AS VARCHAR(10)) AS DIR9_country_code,
	    CAST(DIR9_STATE AS VARCHAR(20)) AS DIR9_STATE,
		CAST(DIR9_OCCUPATION AS VARCHAR(99)) AS DIR9_OCCUPATION,
	    CAST(CASE WHEN DIR9_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR9_ROLE END AS VARCHAR(10)) AS DIR9_ROLE,
		------------------------------------- DIRECTOR 10 -----------------------------------------
		CAST(DIR10_GNDR AS VARCHAR(10)) AS DIR10_GNDR,
		CAST(DIR10_TITL AS VARCHAR(10)) AS DIR10_TITL,
		CAST(DIR10_FIRSTNAME AS VARCHAR(99)) AS DIR10_FIRSTNAME,
		CAST(DIR10_LASTNAME AS VARCHAR(99)) AS DIR10_LASTNAME,
		CAST(DIR10_FATHER_NAME AS VARCHAR(99)) AS DIR10_FATHER_NAME,
		CAST(DIR10_SSN_TYPE AS VARCHAR(10)) AS DIR10_SSN_TYPE,
		CAST(CASE WHEN DIR10_SSN_TYPE IN ('NIC', 'PPT','POC')THEN DIR10_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS DIR10_SSN,
	    CAST(DIR10_nationality1 AS VARCHAR(10)) AS DIR10_nationality1,
	    CAST(DIR10_Residence AS VARCHAR(10)) AS DIR10_Residence,
	    CAST(DIR10_tph_contact_type AS VARCHAR(10)) AS DIR10_tph_contact_type,
	    CAST(DIR10_tph_communication_type AS VARCHAR(10)) AS DIR10_tph_communication_type,
	    CAST(DIR10_tph_country_prefix AS VARCHAR(10)) AS DIR10_tph_country_prefix,
		CAST(DIR10_TPH_NUMBER AS VARCHAR(20)) AS DIR10_TPH_NUMBER,
		CAST(CASE WHEN DIR10_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(DIR10_DATE_OF_BIRTH, 3) ELSE DIR10_DATE_OF_BIRTH END AS VARCHAR(20)) AS DIR10_DATE_OF_BIRTH,
	    CAST(DIR10_address_type AS VARCHAR(10)) AS DIR10_address_type,
		CAST(DIR10_ADDRESS AS VARCHAR(99)) AS DIR10_ADDRESS,
	    CAST(DIR10_CITY AS VARCHAR(20)) AS DIR10_CITY,
	    CAST(DIR10_country_code AS VARCHAR(10)) AS DIR10_country_code,
	    CAST(DIR10_STATE AS VARCHAR(20)) AS DIR10_STATE,
		CAST(DIR10_OCCUPATION AS VARCHAR(99)) AS DIR10_OCCUPATION,
	    CAST(CASE WHEN DIR10_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE DIR10_ROLE END AS VARCHAR(10)) AS DIR10_ROLE,
		------------------------------------------- TFMC TAX NUM ------------------------------------------------------------
		CAST(TFMC_TAX_NUM AS VARCHAR(99)) AS TFMC_TAX_NUM,
		--------------------------------------------- SIGNATORY 1 ----------------------------------------------------
		 CAST(SIGNATORY1_IS_PRIMARY AS VARCHAR(10)) AS SIGNATORY1_IS_PRIMARY,
		CAST(SIGNATORY1_GNDR AS VARCHAR(10)) AS SIGNATORY1_GNDR,
		CAST(SIGNATORY1_TITL AS VARCHAR(10)) AS SIGNATORY1_TITL,
		CAST(SIGNATORY1_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY1_FIRSTNAME,
		CAST(SIGNATORY1_LASTNAME AS VARCHAR(99)) AS SIGNATORY1_LASTNAME,
		CAST(SIGNATORY1_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY1_FATHER_NAME,
		CAST(SIGNATORY1_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY1_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY1_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY1_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY1_SSN,   
	    CAST(SIGNATORY1_nationality1 AS VARCHAR(10)) AS SIGNATORY1_nationality1,
	    CAST(SIGNATORY1_Residence AS VARCHAR(10)) AS SIGNATORY1_Residence,
	    CAST(SIGNATORY1_tph_contact_type AS VARCHAR(10)) AS SIGNATORY1_tph_contact_type,
	    CAST(SIGNATORY1_tph_communication_type AS VARCHAR(10)) AS SIGNATORY1_tph_communication_type,	
	    CAST(SIGNATORY1_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY1_tph_country_prefix,
		CAST(CASE WHEN SIGNATORY1_TPH_NUMBER IS NULL OR SIGNATORY1_TPH_NUMBER = '' THEN 
                  COALESCE(CASE WHEN DIR1_TPH_NUMBER IS NULL OR DIR1_TPH_NUMBER = '' THEN TTMC_tph_number END, DIR1_TPH_NUMBER ) ELSE SIGNATORY1_TPH_NUMBER END AS VARCHAR(50)) AS SIGNATORY1_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY1_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY1_DATE_OF_BIRTH, 3) ELSE SIGNATORY1_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY1_DATE_OF_BIRTH,
	    CAST(SIGNATORY1_address_type AS VARCHAR(20)) AS SIGNATORY1_address_type,
		CAST(SIGNATORY1_ADDRESS AS VARCHAR(99)) AS SIGNATORY1_ADDRESS,
	    CAST(SIGNATORY1_CITY AS VARCHAR(20)) AS SIGNATORY1_CITY,
	    CAST(SIGNATORY1_country_code AS VARCHAR(10)) AS SIGNATORY1_country_code,
	    CAST(SIGNATORY1_STATE AS VARCHAR(20)) AS SIGNATORY1_STATE,
		CAST(SIGNATORY1_OCCUPATION AS VARCHAR(99)) AS SIGNATORY1_OCCUPATION,
	    CAST(SIGNATORY1_ROLE AS VARCHAR(10)) AS SIGNATORY1_ROLE,
		--------------------------------------------- SIGNATORY 2 ----------------------------------------------------
	    CAST(CASE WHEN SIGNATORY2_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY2_IS_PRIMARY END AS VARCHAR(10)) AS SIGNATORY2_IS_PRIMARY,
		CAST(SIGNATORY2_GNDR AS VARCHAR(10)) AS SIGNATORY2_GNDR,
		CAST(SIGNATORY2_TITL AS VARCHAR(10)) AS SIGNATORY2_TITL,
		CAST(SIGNATORY2_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY2_FIRSTNAME,
		CAST(SIGNATORY2_LASTNAME AS VARCHAR(99)) AS SIGNATORY2_LASTNAME,
		CAST(SIGNATORY2_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY2_FATHER_NAME,
		CAST(SIGNATORY2_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY2_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY2_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY2_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY2_SSN,
	    CAST(SIGNATORY2_nationality1 AS VARCHAR(10)) AS SIGNATORY2_nationality1,
	    CAST(SIGNATORY2_Residence AS VARCHAR(10)) AS SIGNATORY2_Residence,
	    CAST(SIGNATORY2_tph_contact_type AS VARCHAR(10)) AS SIGNATORY2_tph_contact_type,
	    CAST(SIGNATORY2_tph_communication_type AS VARCHAR(10)) AS SIGNATORY2_tph_communication_type,	
	    CAST(SIGNATORY2_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY2_tph_country_prefix,
		CAST(SIGNATORY2_TPH_NUMBER AS VARCHAR(50)) AS SIGNATORY2_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY2_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY2_DATE_OF_BIRTH, 3) ELSE SIGNATORY2_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY2_DATE_OF_BIRTH,
	    CAST(SIGNATORY2_address_type AS VARCHAR(20)) AS SIGNATORY2_address_type,
		CAST(SIGNATORY2_ADDRESS AS VARCHAR(99)) AS SIGNATORY2_ADDRESS,
	    CAST(SIGNATORY2_CITY AS VARCHAR(20)) AS SIGNATORY2_CITY,
	    CAST(SIGNATORY2_country_code AS VARCHAR(10)) AS SIGNATORY2_country_code,
	    CAST(SIGNATORY2_STATE AS VARCHAR(20)) AS SIGNATORY2_STATE,
		CAST(SIGNATORY2_OCCUPATION AS VARCHAR(99)) AS SIGNATORY2_OCCUPATION,
	    CAST(CASE WHEN SIGNATORY2_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY2_ROLE END AS VARCHAR(10)) AS SIGNATORY2_ROLE,
        --------------------------------------------- SIGNATORY 3 ----------------------------------------------------
	    CAST(CASE WHEN SIGNATORY3_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY3_IS_PRIMARY END AS VARCHAR(10)) AS SIGNATORY3_IS_PRIMARY,
		CAST(SIGNATORY3_GNDR AS VARCHAR(10)) AS SIGNATORY3_GNDR,
		CAST(SIGNATORY3_TITL AS VARCHAR(10)) AS SIGNATORY3_TITL,
		CAST(SIGNATORY3_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY3_FIRSTNAME,
		CAST(SIGNATORY3_LASTNAME AS VARCHAR(99)) AS SIGNATORY3_LASTNAME,
		CAST(SIGNATORY3_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY3_FATHER_NAME,
		CAST(SIGNATORY3_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY3_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY3_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY3_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY3_SSN,
	    CAST(SIGNATORY3_nationality1 AS VARCHAR(10)) AS SIGNATORY3_nationality1,
	    CAST(SIGNATORY3_Residence AS VARCHAR(10)) AS SIGNATORY3_Residence,
	    CAST(SIGNATORY3_tph_contact_type AS VARCHAR(10)) AS SIGNATORY3_tph_contact_type,
	    CAST(SIGNATORY3_tph_communication_type AS VARCHAR(10)) AS SIGNATORY3_tph_communication_type,	
	    CAST(SIGNATORY3_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY3_tph_country_prefix,
		CAST(SIGNATORY3_TPH_NUMBER AS VARCHAR(50)) AS SIGNATORY3_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY3_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY3_DATE_OF_BIRTH, 3) ELSE SIGNATORY3_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY3_DATE_OF_BIRTH,
	    CAST(SIGNATORY3_address_type AS VARCHAR(20)) AS SIGNATORY3_address_type,
		CAST(SIGNATORY3_ADDRESS AS VARCHAR(99)) AS SIGNATORY3_ADDRESS,
	    CAST(SIGNATORY3_CITY AS VARCHAR(20)) AS SIGNATORY3_CITY,
	    CAST(SIGNATORY3_country_code AS VARCHAR(10)) AS SIGNATORY3_country_code,
	    CAST(SIGNATORY3_STATE AS VARCHAR(20)) AS SIGNATORY3_STATE,
		CAST(SIGNATORY3_OCCUPATION AS VARCHAR(99)) AS SIGNATORY3_OCCUPATION,
	    CAST(CASE WHEN SIGNATORY3_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY3_ROLE END AS VARCHAR(10)) AS SIGNATORY3_ROLE,
		--------------------------------------------- SIGNATORY 4 ----------------------------------------------------
	    CAST(CASE WHEN SIGNATORY4_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY4_IS_PRIMARY END AS VARCHAR(10)) AS SIGNATORY4_IS_PRIMARY,
		CAST(SIGNATORY4_GNDR AS VARCHAR(10)) AS SIGNATORY4_GNDR,
		CAST(SIGNATORY4_TITL AS VARCHAR(10)) AS SIGNATORY4_TITL,
		CAST(SIGNATORY4_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY4_FIRSTNAME,
		CAST(SIGNATORY4_LASTNAME AS VARCHAR(99)) AS SIGNATORY4_LASTNAME,
		CAST(SIGNATORY4_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY4_FATHER_NAME,
		CAST(SIGNATORY4_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY4_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY4_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY4_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY4_SSN,
	    CAST(SIGNATORY4_nationality1 AS VARCHAR(10)) AS SIGNATORY4_nationality1,
	    CAST(SIGNATORY4_Residence AS VARCHAR(10)) AS SIGNATORY4_Residence,
	    CAST(SIGNATORY4_tph_contact_type AS VARCHAR(10)) AS SIGNATORY4_tph_contact_type,
	    CAST(SIGNATORY4_tph_communication_type AS VARCHAR(10)) AS SIGNATORY4_tph_communication_type,	
	    CAST(SIGNATORY4_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY4_tph_country_prefix,
		CAST(SIGNATORY4_TPH_NUMBER AS VARCHAR(50)) AS SIGNATORY4_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY4_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY4_DATE_OF_BIRTH, 3) ELSE SIGNATORY4_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY4_DATE_OF_BIRTH,
	    CAST(SIGNATORY4_address_type AS VARCHAR(20)) AS SIGNATORY4_address_type,
		CAST(SIGNATORY4_ADDRESS AS VARCHAR(99)) AS SIGNATORY4_ADDRESS,
	    CAST(SIGNATORY4_CITY AS VARCHAR(20)) AS SIGNATORY4_CITY,
	    CAST(SIGNATORY4_country_code AS VARCHAR(10)) AS SIGNATORY4_country_code,
	    CAST(SIGNATORY4_STATE AS VARCHAR(20)) AS SIGNATORY4_STATE,
		CAST(SIGNATORY4_OCCUPATION AS VARCHAR(99)) AS SIGNATORY4_OCCUPATION,
	    CAST(CASE WHEN SIGNATORY4_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY4_ROLE END AS VARCHAR(10)) AS SIGNATORY4_ROLE,
		--------------------------------------------- SIGNATORY 5 ----------------------------------------------------
	    CAST(CASE WHEN SIGNATORY5_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY5_IS_PRIMARY END AS VARCHAR(10)) AS SIGNATORY5_IS_PRIMARY,
		CAST(SIGNATORY5_GNDR AS VARCHAR(10)) AS SIGNATORY5_GNDR,
		CAST(SIGNATORY5_TITL AS VARCHAR(10)) AS SIGNATORY5_TITL,
		CAST(SIGNATORY5_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY5_FIRSTNAME,
		CAST(SIGNATORY5_LASTNAME AS VARCHAR(99)) AS SIGNATORY5_LASTNAME,
		CAST(SIGNATORY5_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY5_FATHER_NAME,
		CAST(SIGNATORY5_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY5_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY5_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY5_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY5_SSN,
	    CAST(SIGNATORY5_nationality1 AS VARCHAR(10)) AS SIGNATORY5_nationality1,
	    CAST(SIGNATORY5_Residence AS VARCHAR(10)) AS SIGNATORY5_Residence,
	    CAST(SIGNATORY5_tph_contact_type AS VARCHAR(10)) AS SIGNATORY5_tph_contact_type,
	    CAST(SIGNATORY5_tph_communication_type AS VARCHAR(10)) AS SIGNATORY5_tph_communication_type,	
	    CAST(SIGNATORY5_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY5_tph_country_prefix,
		CAST(SIGNATORY5_TPH_NUMBER AS VARCHAR(50)) AS SIGNATORY5_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY5_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY5_DATE_OF_BIRTH, 3) ELSE SIGNATORY5_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY5_DATE_OF_BIRTH,
	    CAST(SIGNATORY5_address_type AS VARCHAR(20)) AS SIGNATORY5_address_type,
		CAST(SIGNATORY5_ADDRESS AS VARCHAR(99)) AS SIGNATORY5_ADDRESS,
	    CAST(SIGNATORY5_CITY AS VARCHAR(20)) AS SIGNATORY5_CITY,
	    CAST(SIGNATORY5_country_code AS VARCHAR(10)) AS SIGNATORY5_country_code,
	    CAST(SIGNATORY5_STATE AS VARCHAR(20)) AS SIGNATORY5_STATE,
		CAST(SIGNATORY5_OCCUPATION AS VARCHAR(99)) AS SIGNATORY5_OCCUPATION,
	    CAST(CASE WHEN SIGNATORY5_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY5_ROLE END AS VARCHAR(10)) AS SIGNATORY5_ROLE,
		--------------------------------------------- SIGNATORY 6 ----------------------------------------------------
	    CAST(CASE WHEN SIGNATORY6_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY6_IS_PRIMARY END AS VARCHAR(10)) AS SIGNATORY6_IS_PRIMARY,
		CAST(SIGNATORY6_GNDR AS VARCHAR(10)) AS SIGNATORY6_GNDR,
		CAST(SIGNATORY6_TITL AS VARCHAR(10)) AS SIGNATORY6_TITL,
		CAST(SIGNATORY6_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY6_FIRSTNAME,
		CAST(SIGNATORY6_LASTNAME AS VARCHAR(99)) AS SIGNATORY6_LASTNAME,
		CAST(SIGNATORY6_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY6_FATHER_NAME,
		CAST(SIGNATORY6_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY6_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY6_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY6_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY6_SSN,
	    CAST(SIGNATORY6_nationality1 AS VARCHAR(10)) AS SIGNATORY6_nationality1,
	    CAST(SIGNATORY6_Residence AS VARCHAR(10)) AS SIGNATORY6_Residence,
	    CAST(SIGNATORY6_tph_contact_type AS VARCHAR(10)) AS SIGNATORY6_tph_contact_type,
	    CAST(SIGNATORY6_tph_communication_type AS VARCHAR(10)) AS SIGNATORY6_tph_communication_type,	
	    CAST(SIGNATORY6_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY6_tph_country_prefix,
		CAST(SIGNATORY6_TPH_NUMBER AS VARCHAR(50)) AS SIGNATORY6_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY6_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY6_DATE_OF_BIRTH, 3) ELSE SIGNATORY6_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY6_DATE_OF_BIRTH,
	    CAST(SIGNATORY6_address_type AS VARCHAR(20)) AS SIGNATORY6_address_type,
		CAST(SIGNATORY6_ADDRESS AS VARCHAR(99)) AS SIGNATORY6_ADDRESS,
	    CAST(SIGNATORY6_CITY AS VARCHAR(20)) AS SIGNATORY6_CITY,
	    CAST(SIGNATORY6_country_code AS VARCHAR(10)) AS SIGNATORY6_country_code,
	    CAST(SIGNATORY6_STATE AS VARCHAR(20)) AS SIGNATORY6_STATE,
		CAST(SIGNATORY6_OCCUPATION AS VARCHAR(99)) AS SIGNATORY6_OCCUPATION,
	    CAST(CASE WHEN SIGNATORY6_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY6_ROLE END AS VARCHAR(10)) AS SIGNATORY6_ROLE,
		--------------------------------------------- SIGNATORY 7 ----------------------------------------------------
	    CAST(CASE WHEN SIGNATORY7_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY7_IS_PRIMARY END AS VARCHAR(10)) AS SIGNATORY7_IS_PRIMARY,
		CAST(SIGNATORY7_GNDR AS VARCHAR(10)) AS SIGNATORY7_GNDR,
		CAST(SIGNATORY7_TITL AS VARCHAR(10)) AS SIGNATORY7_TITL,
		CAST(SIGNATORY7_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY7_FIRSTNAME,
		CAST(SIGNATORY7_LASTNAME AS VARCHAR(99)) AS SIGNATORY7_LASTNAME,
		CAST(SIGNATORY7_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY7_FATHER_NAME,
		CAST(SIGNATORY7_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY7_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY7_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY7_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY7_SSN,
	    CAST(SIGNATORY7_nationality1 AS VARCHAR(10)) AS SIGNATORY7_nationality1,
	    CAST(SIGNATORY7_Residence AS VARCHAR(10)) AS SIGNATORY7_Residence,
	    CAST(SIGNATORY7_tph_contact_type AS VARCHAR(10)) AS SIGNATORY7_tph_contact_type,
	    CAST(SIGNATORY7_tph_communication_type AS VARCHAR(10)) AS SIGNATORY7_tph_communication_type,	
	    CAST(SIGNATORY7_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY7_tph_country_prefix,
		CAST(SIGNATORY7_TPH_NUMBER AS VARCHAR(50)) AS SIGNATORY7_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY7_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY7_DATE_OF_BIRTH, 3) ELSE SIGNATORY7_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY7_DATE_OF_BIRTH,
	    CAST(SIGNATORY7_address_type AS VARCHAR(20)) AS SIGNATORY7_address_type,
		CAST(SIGNATORY7_ADDRESS AS VARCHAR(99)) AS SIGNATORY7_ADDRESS,
	    CAST(SIGNATORY7_CITY AS VARCHAR(20)) AS SIGNATORY7_CITY,
	    CAST(SIGNATORY7_country_code AS VARCHAR(10)) AS SIGNATORY7_country_code,
	    CAST(SIGNATORY7_STATE AS VARCHAR(20)) AS SIGNATORY7_STATE,
		CAST(SIGNATORY7_OCCUPATION AS VARCHAR(99)) AS SIGNATORY7_OCCUPATION,
	    CAST(CASE WHEN SIGNATORY7_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY7_ROLE END AS VARCHAR(10)) AS SIGNATORY7_ROLE,
		--------------------------------------------- SIGNATORY 8 ----------------------------------------------------
	    CAST(CASE WHEN SIGNATORY8_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY8_IS_PRIMARY END AS VARCHAR(10)) AS SIGNATORY8_IS_PRIMARY,
		CAST(SIGNATORY8_GNDR AS VARCHAR(10)) AS SIGNATORY8_GNDR,
		CAST(SIGNATORY8_TITL AS VARCHAR(10)) AS SIGNATORY8_TITL,
		CAST(SIGNATORY8_FIRSTNAME AS VARCHAR(99)) AS SIGNATORY8_FIRSTNAME,
		CAST(SIGNATORY8_LASTNAME AS VARCHAR(99)) AS SIGNATORY8_LASTNAME,
		CAST(SIGNATORY8_FATHER_NAME AS VARCHAR(99)) AS SIGNATORY8_FATHER_NAME,
		CAST(SIGNATORY8_SSN_TYPE AS VARCHAR(10)) AS SIGNATORY8_SSN_TYPE,
		CAST(CASE WHEN SIGNATORY8_SSN_TYPE IN ('NIC', 'PPT','POC') THEN SIGNATORY8_SSN ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS SIGNATORY8_SSN,
	    CAST(SIGNATORY8_nationality1 AS VARCHAR(10)) AS SIGNATORY8_nationality1,
	    CAST(SIGNATORY8_Residence AS VARCHAR(10)) AS SIGNATORY8_Residence,
	    CAST(SIGNATORY8_tph_contact_type AS VARCHAR(10)) AS SIGNATORY8_tph_contact_type,
	    CAST(SIGNATORY8_tph_communication_type AS VARCHAR(10)) AS SIGNATORY8_tph_communication_type,	
	    CAST(SIGNATORY8_tph_country_prefix AS VARCHAR(10)) AS SIGNATORY8_tph_country_prefix,
		CAST(SIGNATORY8_TPH_NUMBER AS VARCHAR(50)) AS SIGNATORY8_TPH_NUMBER,
		CAST(CASE WHEN SIGNATORY8_DATE_OF_BIRTH LIKE '00%'  THEN '19' || SUBSTR(SIGNATORY8_DATE_OF_BIRTH, 3) ELSE SIGNATORY8_DATE_OF_BIRTH END AS VARCHAR(20)) AS SIGNATORY8_DATE_OF_BIRTH,
	    CAST(SIGNATORY8_address_type AS VARCHAR(20)) AS SIGNATORY8_address_type,
		CAST(SIGNATORY8_ADDRESS AS VARCHAR(99)) AS SIGNATORY8_ADDRESS,
	    CAST(SIGNATORY8_CITY AS VARCHAR(20)) AS SIGNATORY8_CITY,
	    CAST(SIGNATORY8_country_code AS VARCHAR(10)) AS SIGNATORY8_country_code,
	    CAST(SIGNATORY8_STATE AS VARCHAR(20)) AS SIGNATORY8_STATE,
		CAST(SIGNATORY8_OCCUPATION AS VARCHAR(99)) AS SIGNATORY8_OCCUPATION,
	    CAST(CASE WHEN SIGNATORY8_FIRSTNAME IS NULL THEN CAST(NULL AS VARCHAR(10)) ELSE SIGNATORY8_ROLE END AS VARCHAR(10)) AS SIGNATORY8_ROLE,
		----------------------------------------- TFMC REMAINGING ---------------------------------------------------------
		CAST(TFMC_open AS VARCHAR(20)) AS TFMC_open,
		CAST(TFMC_status_code AS VARCHAR(10)) AS TFMC_status_code,
		CAST(TFMC_from_country AS VARCHAR(10)) AS TFMC_from_country,
		--------------------------------------- TO MY CLEINT TAG -----------------------------------------------------------
		CAST(TTMC_to_funds_code AS VARCHAR(10)) AS TTMC_to_funds_code,
		CAST(TTMC_Gender AS VARCHAR(10)) AS TTMC_Gender,
		CAST(TTMC_Title AS VARCHAR(99)) AS TTMC_Title,
		CAST(TTMC_First_Name AS VARCHAR(99)) AS TTMC_First_Name,
		CAST(TTMC_Last_Name AS VARCHAR(99)) AS TTMC_Last_Name,
		CAST(CASE WHEN TTMC_Birth_Date LIKE '00%'  THEN '19' || SUBSTR(TTMC_Birth_Date, 3) ELSE TTMC_Birth_Date END AS VARCHAR(20)) AS TTMC_Birth_Date,
		CAST(TTMC_Mother_Name AS VARCHAR(99)) AS TTMC_Mother_Name,
		CAST(TTMC_ssn_type AS VARCHAR(10)) AS TTMC_ssn_type,
		CAST(CASE WHEN TTMC_ssn_type IN ('NIC', 'PPT', 'POC') THEN TTMC_ssn ELSE CAST(NULL AS VARCHAR(10)) END AS VARCHAR(20)) AS TTMC_ssn,		
		CAST(CASE WHEN TTMC_ssn_type= 'NIC' THEN 'PK' ELSE TTMC_nationality1 END  AS VARCHAR(20)) AS TTMC_nationality1, 
		CAST(TTMC_Residence AS VARCHAR(20)) AS TTMC_Residence,
		CAST(TTMC_tph_contact_type AS VARCHAR(20)) AS TTMC_tph_contact_type,
		CAST(TTMC_tph_communication_type AS VARCHAR(20)) AS TTMC_tph_communication_type,
		CAST(TTMC_tph_country_prefix AS VARCHAR(10)) AS TTMC_tph_country_prefix,
		CAST(TTMC_tph_number AS VARCHAR(20)) AS TTMC_tph_number,
		CAST(TTMC_address_type AS VARCHAR(10)) AS TTMC_address_type,
		CAST(TTMC_address AS VARCHAR(99)) AS TTMC_address,
		CAST(TTMC_city AS VARCHAR(50)) AS TTMC_city,
		CAST(TTMC_country_code AS VARCHAR(10)) AS TTMC_country_code,
		CAST(TTMC_state AS VARCHAR(50)) AS TTMC_state,
		CAST(TTMC_occupation AS VARCHAR(99)) AS TTMC_occupation,
		CAST(TTMC_to_country AS VARCHAR(20)) AS TTMC_to_country
		FROM Final_Chunk 
		) 
		

		SELECT * FROM DATA_V1 
		WHERE CATEGORY = '{entity_individual_flag}' ;
		
		"""
    
    
	
	
	
	return query






def check_query():
	query = rf"""
	
			WITH TABLE_CHECK AS (
	SELECT 'DP_SDMT_DFDN.DIM_RTAIL_BNK_ACCT_JNT' AS "TABLE_NAME", MAX(START_DATE) MAX_DATE FROM DP_SDMT_DFDN.DIM_RTAIL_BNK_ACCT_JNT
	UNION ALL
	SELECT 'DP_SDMVW_DFDN.FCT_CURY_EXCH_RATE_VW' AS "TABLE_NAME", MAX(START_DATE) MAX_DATE FROM DP_SDMVW_DFDN.FCT_CURY_EXCH_RATE_VW
	UNION ALL
	SELECT 'DP_REPORTING_MART.TM_DM_MD_MANDATE_AUTHORIZE' AS "TABLE_NAME", MAX(START_DATE) MAX_DATE FROM DP_REPORTING_MART.TM_DM_MD_MANDATE_AUTHORIZE
	UNION ALL
	SELECT 'DP_REPORTING_MART.FM_DIRECTOR_DTLS' AS "TABLE_NAME", MAX(START_DATE) MAX_DATE FROM DP_REPORTING_MART.FM_DIRECTOR_DTLS
	UNION ALL
	SELECT 'DP_SDMT_DFDN.WALKIN_TXN' AS "TABLE_NAME", MAX(START_DATE) MAX_DATE FROM DP_SDMT_DFDN.WALKIN_TXN
	UNION ALL
	SELECT 'DP_WRK_CBS.FM_CLIENT_DAILY' AS "TABLE_NAME", MAX(START_DATE) MAX_DATE FROM DP_WRK_CBS.FM_CLIENT_DAILY
	)

	SELECT  CASE WHEN SUM(CASE WHEN MAX_DATE IS NULL THEN 1 ELSE 0 END) = 0 THEN 'READY' ELSE 'TABLES UPDATING' END AS STATUS FROM TABLE_CHECK;
	
	"""
	return query