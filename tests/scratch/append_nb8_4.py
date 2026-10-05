import json
p = r'C:\Users\santiago\Desktop\unal\analitica predictiva\std-santiago-ramos-galvis\PRE_08_series_de_tiempo\notebooks\notebook_8.ipynb'
nb = json.load(open(p, encoding='utf-8'))
nb['cells'].append({'cell_type':'code','execution_count':None,'metadata':{},'outputs':[],'source':[
 '#\n',
 '# Entrenamiento y pronostico\n',
 '#\n',
 'hidden = 4\n',
 'pipeline = make_pipeline_from_model(\n',
 '    model=MLPRegressor(\n',
 '        hidden_layer_sizes=(hidden,),\n',
 '        activation="logistic",\n',
 '        learning_rate="adaptive",\n',
 '        momentum=0.01,\n',
 '        learning_rate_init=0.2,\n',
 '        max_iter=10000,\n',
 '        random_state=12345,\n',
 '    )\n',
 ')\n',
 'pipeline.fit(X_train, y_train)\n',
 '\n',
 'df_dropna[f"yt_d1d12_mlp"] = pipeline.predict(X_complete)\n',
 'df_orig.loc[df_dropna.index, "yt_d1d12_mlp"] = df_dropna[f"yt_d1d12_mlp"]\n',
 'df_orig[\n',
 '    [\n',
 '        "yt_true",\n',
 '        "yt_true_d1d12",\n',
 '        f"yt_d1d12_mlp",\n',
 '    ]\n',
 '].head(40)'
]})
json.dump(nb, open(p,'w',encoding='utf-8'), indent=1, ensure_ascii=False)
print('ok', len(nb['cells']))
