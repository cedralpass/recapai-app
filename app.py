from werkzeug.middleware.dispatcher import DispatcherMiddleware # use to combine each Flask app into a larger one that is dispatched based on prefix
import recap
import aiapi

print ("lanuching webserver with merged apps")
application = DispatcherMiddleware(recap.create_app(), {
    '/aiapi': aiapi.create_app()
})