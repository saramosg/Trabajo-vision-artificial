import json
p = r'C:\Users\santiago\Desktop\unal\analitica predictiva\std-santiago-ramos-galvis\PRE_08_series_de_tiempo\notebooks\notebook_8.ipynb'
nb = json.load(open(p, encoding='utf-8'))
nb['cells'].append({'cell_type':'code','execution_count':None,'metadata':{},'outputs':[],'source':[
 '#\n',
 '# Pronostico usando una red neuronal tipo MLP\n',
 '#\n',
 'from sklearn.pipeline import Pipeline  # type: ignore\n',
 'from sklearn.preprocessing import MinMaxScaler  # type: ignore\n',
 'from sklearn.compose import TransformedTargetRegressor  # type: ignore\n',
 'from sklearn.neural_network import MLPRegressor  # type: ignore\n',
 '\n',
 '# Crea un pipeline para automatizar la creacion de un modelo\n',
 'def make_pipeline_from_model(model):\n',
 '    """Create a pipeline."""\n',
 '    return Pipeline(\n',
 '        [\n',
 '            (\n',
 '                "scaler",\n',
 '                MinMaxScaler(),\n',
 '            ),\n',
 '            (\n',
 '                "regressor",\n',
 '                TransformedTargetRegressor(\n',
 '                    regressor=model,\n',
 '                    transformer=MinMaxScaler(),\n',
 '                ),\n',
 '            ),\n',
 '        ]\n',
 '    )'
]})
json.dump(nb, open(p,'w',encoding='utf-8'), indent=1, ensure_ascii=False)
print('ok', len(nb['cells']))
