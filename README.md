## Fraud detection async-service

Сервис анализирует текстовые сообщения, расчитывает вероятность принадлежности данного сообщения 
к мошенническим сообщениям. С сервером можно обмениваться данными по http и websocket протоколам, данные должны 
передаваться в формате json.

1. ``frauddetectionapp``. Приложение асинхронно обрабатывает http/websocket запросы.
    1. Запуск приложения.
        
        Необходимо в файле ``docs/gunicorn.conf`` задать ``host:port`` в поле ``bind`` по которому будет доступно приложение, 
        а так же количество процессов в поле ``workers`` в которых будут запущены инстансы приложения. 
        Для запуска приложения, необходимо выполнить команды ниже.  
        
        - ``cd frauddetectionapp/``
        - ``gunicorn process:application -c docs/gunicorn.conf`` 
    
    2. Использование приложения.
        
        1) HTTP protocol. Request and response queries.
            - Request query:
                ````
                curl -X POST -d '{ 
                        "text": [
                            "Уважаемый, клиент. Ваша банковская карта заблокирована, просим вас обратиться по номеру 88006009898 ", 
                            "Привет, дружок, как ты?"
                        ]
                    }' http://<host>:<port>/predict/scores
                ```` 
            - Response query:
                ````
                    {
                        "message": {
                            "scores": [0.9986685514450073, 0.00032561086118221283]
                        },
                        "status": "success"
                    }
                ````   
        2) Websocket protocol. Connection query, send request data and receive response data.
            - Connection query:
                ````
                ws://<host>:<port>/ws/predict/scores
                ````
            - Send request data:
                ````
                    {
                        "text": [
                            "Уважаемый, клиент. Ваша банковская карта заблокирована, просим вас обратиться по номеру 88006009898 ", 
                            "Привет, дружок, как ты?"
                        ]
                    }
                ````
            - Receive response data:
                ````
                    {
                        "message": {
                            "scores": [0.9986685514450073, 0.00032561086118221283]
                        },
                        "status": "success"
                    }
                    
            ````
2. ``frauddetectionclient``. Приложение подключается к серверу и получает сообщения по протоколу websocket. Расчитывает
    скоринг, далее откидывает результат в elasticsearch. Необходимо предварительно настроить elsticsearch и logstash. Перед тем как запустить приложение, необходимо запустить logstash с указанием конфига. 

    - ``bin/logstash -f docs/logstash.conf``
       
      Запустить приложение
        
    - ``cd frauddetectionclient/ ``
    
    - ``python3.5 process.py --config docs/application.yml`` 
       