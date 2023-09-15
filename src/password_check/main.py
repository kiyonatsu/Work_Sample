import pandas as pd

from src.password_check.ck_pwd import check_password

functional = pd.read_csv("data/cred_functional.csv")
subcon = pd.read_csv("data/cred_subcontractor.csv")
func_username = functional.username.values.tolist()
subcon_username = subcon.username.values.tolist()


# Full List of Thingies
myUserNames = ["hcoverit", "nokiacas", "hartifac", "hprm", "salesfor", "hconflue", "espares", \
               "hcsuppor", "sappi", "extranet", "plcmxmc", "hsponlin", "pvoip", "voip", "perfvoip", \
               "pevoip", "heedatad", "procure2", "hsitefor", "ohclapm", "ipmepm1", "e2brsaop", \
               "E2CNBEIJ", "E2DEMUNI", "einbanga", "e2brsaop", "eusirvin", "E2CNBEIJ", \
               "E2DEMUNI", "einbanga", "e2brsaop", "E2CNBEIJ", "E2DEMUNI", "einbanga", \
               "eejmonpr", "PERFMON", "heemagic", "ee4labs", "hsonarqu", "hespares", \
               "hcespare", "hclespar", "hcleespa", "hcle2esp", "hcle2ees", "hcle2eme", \
               "h1espare", "h2espare", "h3espare", "h4espare", "h5espare", "h6espare", \
               "hcletoem", "ehcletoe", "emhcleto", "emahclet", "emaihcle", "hprocure", \
               "hcprocur", "hclprocu", "hcleproc", "hcle2pro", "hcmytool", "pelawson", \
               "pbluepla", "aled", "clics", "aslm", "pallianc", "pimagepl", "virtualc", \
               "pebluepl", "perbluep", "perfblue", "perfoblu", "perforbl", "performb", \
               "p1bluepl", "pvertex"]
myUserNames2 = ["hcoverit", "hartifac", \
                "hcsuppor", "plcmxmc", \
                "pevoip", "heedatad", "procure2", "hsitefor", "ipmepm1", \
                "E2DEMUNI", \
                "PERFMON", "hespares", \
                "emaihcle", "procure2", \
                "hcmytool", "pelawson", \
                "pbluepla", "aled", "clics", "aslm", "pallianc", "pimagepl", "virtualc", \
                ]

myUserNames3 = ["hconflue"]

print("This is the result for functional user")
check_password(func_username, username_type="functional")
print("This is the result for subcontractor user")
check_password(subcon_username, username_type="subcontractor")