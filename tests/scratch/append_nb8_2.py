import json
p = r'C:\Users\santiago\Desktop\unal\analitica predictiva\std-santiago-ramos-galvis\PRE_08_series_de_tiempo\notebooks\notebook_8.ipynb'
nb = json.load(open(p, encoding='utf-8'))
nb['cells'].append({'cell_type':'code','execution_count':None,'metadata':{},'outputs':[],'source':[
 '#\n',
 '# Remocion de los valores faltantes\n',
 '#\n',
 'df_dropna = df_orig.dropna()\n',
 'df_dropna.head()'
]})
nb['cells'].append({'cell_type':'code','execution_count':None,'metadata':{},'outputs':[],'source':[
 '#\n',
 '# Division de los datos en entrenamiento y prueba\n',
 '#\n',
 '(\n',
 '    X_complete,\n',
 '    y_complete,\n',
 '    X_train,\n',
 '    y_train,\n',
 '    X_test,\n',
 '    y_test,\n',
 ') = functions.train_test_split(\n',
 '    df=df_dropna,\n',
 '    x_columns=[f"lagged_{i}m" for i in range(1, 14)],\n',
 '    y_column="yt_true_d1d12",\n',
 ')\n',
 'display(X_complete.head())\n',
 'display(y_complete.head())'
]})
json.dump(nb, open(p,'w',encoding='utf-8'), indent=1, ensure_ascii=False)
print('ok', len(nb['cells']))
