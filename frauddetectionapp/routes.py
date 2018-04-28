import views


def setup_routes(app):
    app.router.add_get('/', views.index)
    app.router.add_get('/predict', views.predict_get)
    app.router.add_post('/predict', views.predict_get)
    app.router.add_get('/predict/scores', views.predict_score_get)
    app.router.add_post('/predict/scores', views.predict_score_post)
    app.router.add_get('/ws/predict/scores', views.predict_score_ws)
    return app
