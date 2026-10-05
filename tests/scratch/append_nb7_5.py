import json
p = r'C:\Users\santiago\Desktop\unal\analitica predictiva\std-santiago-ramos-galvis\PRE_08_series_de_tiempo\notebooks\notebook_7.ipynb'
nb = json.load(open(p, encoding='utf-8'))
nb['cells'].append({'cell_type':'code','execution_count':None,'metadata':{},'outputs':[],'source':[
 '#\n',
 '# Pronostico usando regresion lineal\n',
 '#\n',
 'from sklearn.linear_model import LinearRegression\n',
 '\n',
 'def create_pipeline():\n',
 '    """Creates a linear regression model."""\n',
 '    return LinearRegression()'
]})
json.dump(nb, open(p,'w',encoding='utf-8'), indent=1, ensure_ascii=False)
print('ok', len(nb['cells']))
