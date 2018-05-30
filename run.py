from app import app
import os
host = os.environ.get('IP', '0.0.0.0')
port = int(os.environ.get('PORT',4331 ))

#app.run(host=host,port=port,debug=True,threaded=True,ssl_context='adhoc')
#app.run(host=host,port=port,debug=True,threaded=True)

if __name__ == "__main__":
    app.run(host=host,port=port,debug=True)
