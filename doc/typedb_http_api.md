TypeDB HTTP API Reference
=========================

Authorization
-------------

### POST /v1/signin

*   **Description**: Request an API token to authenticate against the rest of the API using user credentials. This token must be used as ACCESS\_TOKEN for other protected methods.
*   **Parameters**:
    *   **Request Body**:
        
            {
                "username": "string",
                "password": "string"
            }
        
        Both fields are required.
    *   **Headers**: None required
*   **Request Format**: JSON in request body
*   **Response Format**:
    *   **200 OK**:
        
            {
                "token": "string"
            }
        
    *   No response body for other status codes
*   **Errors**:
    *   **400 Bad Request**: Incorrectly formatted request
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **401 Unauthorized**: Invalid credentials
        
            {
                "code": "string",
                "message": "string"
            }
        
*   **Authentication**: Not required \[[TypeDB | Docs > Reference > Ty...](https://typedb.com/docs/reference/typedb-http-api/)\]

Server Information
------------------

### GET /v1/version

*   **Description**: Get the server's distribution and version information.
*   **Parameters**: None
*   **Request Format**: No request body
*   **Response Format**:
    *   **200 OK**:
        
            {
                "distribution": "string",
                "version": "string"
            }
        
*   **Errors**: None documented
*   **Authentication**: Not required \[[TypeDB | Docs > Reference > Ty...](https://typedb.com/docs/reference/typedb-http-api/)\]

Health Check
------------

### GET /health

*   **Description**: Check that the server is accessible and healthy.
*   **Parameters**: None
*   **Request Format**: No request body
*   **Response Format**:
    *   **204 No Content**: No response body
*   **Errors**: None documented
*   **Authentication**: Not required \[[TypeDB | Docs > Reference > Ty...](https://typedb.com/docs/reference/typedb-http-api/)\]

Database Management
-------------------

### GET /v1/databases

*   **Description**: Get all databases present on the server.
*   **Parameters**:
    *   **Headers**: Authorization: Bearer ACCESS\_TOKEN
*   **Request Format**: No request body
*   **Response Format**:
    *   **200 OK**:
        
            {
                "databases": [
                    {
                        "name": "string"
                    }
                ]
            }
        
*   **Errors**:
    *   **401 Unauthorized**: Invalid or expired token
        
            {
                "code": "string",
                "message": "string"
            }
        
*   **Authentication**: Required \[[TypeDB | Docs > Reference > Ty...](https://typedb.com/docs/reference/typedb-http-api/)\]

### GET /v1/databases/{DATABASE\_NAME}

*   **Description**: Get a single database present on the server by name.
*   **Parameters**:
    *   **Path Parameters**:
        *   DATABASE\_NAME (string, required): Name of the database
    *   **Headers**: Authorization: Bearer ACCESS\_TOKEN
*   **Request Format**: No request body
*   **Response Format**:
    *   **200 OK**:
        
            {
                "name": "string"
            }
        
*   **Errors**:
    *   **401 Unauthorized**: Invalid or expired token
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **404 Not Found**: Database not found
        
            {
                "code": "string",
                "message": "string"
            }
        
*   **Authentication**: Required \[[TypeDB | Docs > Reference > Ty...](https://typedb.com/docs/reference/typedb-http-api/)\]

### POST /v1/databases/{DATABASE\_NAME}

*   **Description**: Create a database on the server.
*   **Parameters**:
    *   **Path Parameters**:
        *   DATABASE\_NAME (string, required): Name of the database to create
    *   **Headers**: Authorization: Bearer ACCESS\_TOKEN
*   **Request Format**: No request body
*   **Response Format**:
    *   **200 OK**: No response body
*   **Errors**:
    *   **400 Bad Request**: Incorrectly formatted request
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **401 Unauthorized**: Invalid or expired token
        
            {
                "code": "string",
                "message": "string"
            }
        
*   **Authentication**: Required \[[TypeDB | Docs > Reference > Ty...](https://typedb.com/docs/reference/typedb-http-api/)\]

### DELETE /v1/databases/{DATABASE\_NAME}

*   **Description**: Delete a database from the server by name.
*   **Parameters**:
    *   **Path Parameters**:
        *   DATABASE\_NAME (string, required): Name of the database to delete
    *   **Headers**: Authorization: Bearer ACCESS\_TOKEN
*   **Request Format**: No request body
*   **Response Format**:
    *   **200 OK**: No response body
*   **Errors**:
    *   **400 Bad Request**: Incorrectly formatted request
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **401 Unauthorized**: Invalid or expired token
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **404 Not Found**: Database not found
        
            {
                "code": "string",
                "message": "string"
            }
        
*   **Authentication**: Required \[[TypeDB | Docs > Reference > Ty...](https://typedb.com/docs/reference/typedb-http-api/)\]

### GET /v1/databases/{DATABASE\_NAME}/schema

*   **Description**: Retrieve a full schema text as a valid TypeQL define query string. This includes function definitions.
*   **Parameters**:
    *   **Path Parameters**:
        *   DATABASE\_NAME (string, required): Name of the database
    *   **Headers**: Authorization: Bearer ACCESS\_TOKEN
*   **Request Format**: No request body
*   **Response Format**:
    *   **200 OK**: String containing TypeQL define query
        
            "define <statements>;"
        
        or empty string if no schema is defined
*   **Errors**:
    *   **400 Bad Request**: Incorrectly formatted request
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **401 Unauthorized**: Invalid or expired token
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **404 Not Found**: Database not found
        
            {
                "code": "string",
                "message": "string"
            }
        
*   **Authentication**: Required \[[TypeDB | Docs > Reference > Ty...](https://typedb.com/docs/reference/typedb-http-api/)\]

### GET /v1/databases/{DATABASE\_NAME}/type-schema

*   **Description**: Retrieve the types in the schema as a valid TypeQL define query string.
*   **Parameters**:
    *   **Path Parameters**:
        *   DATABASE\_NAME (string, required): Name of the database
    *   **Headers**: Authorization: Bearer ACCESS\_TOKEN
*   **Request Format**: No request body
*   **Response Format**:
    *   **200 OK**: String containing TypeQL define query
        
            "define <statements>;"
        
        or empty string if no schema is defined
*   **Errors**:
    *   **400 Bad Request**: Incorrectly formatted request
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **401 Unauthorized**: Invalid or expired token
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **404 Not Found**: Database not found
        
            {
                "code": "string",
                "message": "string"
            }
        
*   **Authentication**: Required \[[TypeDB | Docs > Reference > Ty...](https://typedb.com/docs/reference/typedb-http-api/)\]

User Management
---------------

### GET /v1/users

*   **Description**: Get all users present on the server.
*   **Parameters**:
    *   **Headers**: Authorization: Bearer ACCESS\_TOKEN
*   **Request Format**: No request body
*   **Response Format**:
    *   **200 OK**:
        
            {
                "users": [
                    {
                        "username": "string"
                    }
                ]
            }
        
*   **Errors**:
    *   **401 Unauthorized**: Invalid or expired token
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **403 Forbidden**: Token lacks required access level
        
            {
                "code": "string",
                "message": "string"
            }
        
*   **Authentication**: Required \[[TypeDB | Docs > Reference > Ty...](https://typedb.com/docs/reference/typedb-http-api/)\]

### GET /v1/users/{USERNAME}

*   **Description**: Get a single user present on the server by name.
*   **Parameters**:
    *   **Path Parameters**:
        *   USERNAME (string, required): Username to retrieve
    *   **Headers**: Authorization: Bearer ACCESS\_TOKEN
*   **Request Format**: No request body
*   **Response Format**:
    *   **200 OK**:
        
            {
                "username": "string"
            }
        
*   **Errors**:
    *   **401 Unauthorized**: Invalid or expired token
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **403 Forbidden**: Token lacks required access level
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **404 Not Found**: User not found
        
            {
                "code": "string",
                "message": "string"
            }
        
*   **Authentication**: Required \[[TypeDB | Docs > Reference > Ty...](https://typedb.com/docs/reference/typedb-http-api/)\]

### POST /v1/users/{USERNAME}

*   **Description**: Create a new user on the server.
*   **Parameters**:
    *   **Path Parameters**:
        *   USERNAME (string, required): Username to create
    *   **Request Body**:
        
            {
                "password": "string"
            }
        
        Password field is required.
    *   **Headers**: Authorization: Bearer ACCESS\_TOKEN
*   **Request Format**: JSON in request body
*   **Response Format**:
    *   **200 OK**: No response body
*   **Errors**:
    *   **400 Bad Request**: Incorrectly formatted request
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **401 Unauthorized**: Invalid or expired token
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **403 Forbidden**: Token lacks required access level
        
            {
                "code": "string",
                "message": "string"
            }
        
*   **Authentication**: Required \[[TypeDB | Docs > Reference > Ty...](https://typedb.com/docs/reference/typedb-http-api/)\]

### PUT /v1/users/{USERNAME}

*   **Description**: Update credentials for a user present on the server.
*   **Parameters**:
    *   **Path Parameters**:
        *   USERNAME (string, required): Username to update
    *   **Request Body**:
        
            {
                "password": "string"
            }
        
        Password field is required.
    *   **Headers**: Authorization: Bearer ACCESS\_TOKEN
*   **Request Format**: JSON in request body
*   **Response Format**:
    *   **200 OK**: No response body
*   **Errors**:
    *   **400 Bad Request**: Incorrectly formatted request
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **401 Unauthorized**: Invalid or expired token
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **403 Forbidden**: Token lacks required access level
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **404 Not Found**: User not found
        
            {
                "code": "string",
                "message": "string"
            }
        
*   **Authentication**: Required \[[TypeDB | Docs > Reference > Ty...](https://typedb.com/docs/reference/typedb-http-api/)\]

### DELETE /v1/users/{USERNAME}

*   **Description**: Delete a user from the server by name.
*   **Parameters**:
    *   **Path Parameters**:
        *   USERNAME (string, required): Username to delete
    *   **Headers**: Authorization: Bearer ACCESS\_TOKEN
*   **Request Format**: No request body
*   **Response Format**:
    *   **200 OK**: No response body
*   **Errors**:
    *   **400 Bad Request**: Incorrectly formatted request
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **401 Unauthorized**: Invalid or expired token
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **403 Forbidden**: Token lacks required access level
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **404 Not Found**: User not found
        
            {
                "code": "string",
                "message": "string"
            }
        
*   **Authentication**: Required \[[TypeDB | Docs > Reference > Ty...](https://typedb.com/docs/reference/typedb-http-api/)\]

Transactions
------------

### POST /v1/transactions/open

*   **Description**: Open a new transaction and receive a unique transaction id.
*   **Parameters**:
    *   **Request Body**:
        
            {
                "databaseName": "string",
                "transactionType": "read" | "write" | "schema",
                "transactionOptions": {
                    "schemaLockAcquireTimeoutMillis": "integer",
                    "transactionTimeoutMillis": "integer"
                }
            }
        
        databaseName and transactionType are required. transactionOptions is optional.
    *   **Headers**: Authorization: Bearer ACCESS\_TOKEN
*   **Request Format**: JSON in request body
*   **Response Format**:
    *   **200 OK**:
        
            {
                "transactionId": "string"
            }
        
*   **Errors**:
    *   **400 Bad Request**: Incorrectly formatted request
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **404 Not Found**: Database not found
        
            {
                "code": "string",
                "message": "string"
            }
        
*   **Authentication**: Required \[[TypeDB | Docs > Reference > Ty...](https://typedb.com/docs/reference/typedb-http-api/)\]

### POST /v1/transactions/{TRANSACTION\_ID}/close

*   **Description**: Close a transaction without preserving its changes by transaction id.
*   **Parameters**:
    *   **Path Parameters**:
        *   TRANSACTION\_ID (string, required): ID of the transaction to close
    *   **Headers**: Authorization: Bearer ACCESS\_TOKEN
*   **Request Format**: No request body
*   **Response Format**:
    *   **200 OK**: No response body
*   **Errors**:
    *   **400 Bad Request**: Incorrectly formatted request
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **403 Forbidden**: Token lacks required access level
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **404 Not Found**: Transaction not found
        
            {
                "code": "string",
                "message": "string"
            }
        
*   **Authentication**: Required \[[TypeDB | Docs > Reference > Ty...](https://typedb.com/docs/reference/typedb-http-api/)\]

### POST /v1/transactions/{TRANSACTION\_ID}/commit

*   **Description**: Commit and close a transaction, preserving its changes on the server.
*   **Parameters**:
    *   **Path Parameters**:
        *   TRANSACTION\_ID (string, required): ID of the transaction to commit
    *   **Headers**: Authorization: Bearer ACCESS\_TOKEN
*   **Request Format**: No request body
*   **Response Format**:
    *   **200 OK**: No response body
*   **Errors**:
    *   **400 Bad Request**: Incorrectly formatted request
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **403 Forbidden**: Token lacks required access level
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **404 Not Found**: Transaction not found
        
            {
                "code": "string",
                "message": "string"
            }
        
*   **Authentication**: Required \[[TypeDB | Docs > Reference > Ty...](https://typedb.com/docs/reference/typedb-http-api/)\]

### POST /v1/transactions/{TRANSACTION\_ID}/rollback

*   **Description**: Roll back the uncommitted changes made via a transaction.
*   **Parameters**:
    *   **Path Parameters**:
        *   TRANSACTION\_ID (string, required): ID of the transaction to roll back
    *   **Headers**: Authorization: Bearer ACCESS\_TOKEN
*   **Request Format**: No request body
*   **Response Format**:
    *   **200 OK**: No response body
*   **Errors**:
    *   **400 Bad Request**: Incorrectly formatted request
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **403 Forbidden**: Token lacks required access level
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **404 Not Found**: Transaction not found
        
            {
                "code": "string",
                "message": "string"
            }
        
*   **Authentication**: Required \[[TypeDB | Docs > Reference > Ty...](https://typedb.com/docs/reference/typedb-http-api/)\]

### POST /v1/transactions/{TRANSACTION\_ID}/query

*   **Description**: Run a query within an open transaction. This endpoint allows running multiple sequential queries before committing.
*   **Parameters**:
    *   **Path Parameters**:
        *   TRANSACTION\_ID (string, required): ID of the transaction
    *   **Request Body**:
        
            {
                "query": "string",
                "queryOptions": {
                    "includeInstanceTypes": "boolean",
                    "answerCountLimit": "integer"
                }
            }
        
        query is required. queryOptions is optional.
    *   **Headers**: Authorization: Bearer ACCESS\_TOKEN
*   **Request Format**: JSON in request body
*   **Response Format**:
    *   **200 OK**:
        
            {
                "queryType": "read" | "write" | "schema",
                "answerType": "ok" | "conceptRows" | "conceptDocuments",
                "answers": [],
                "warning": "string"
            }
        
*   **Errors**:
    *   **400 Bad Request**: Incorrectly formatted request
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **403 Forbidden**: Token lacks required access level
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **404 Not Found**: Transaction not found
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **408 Request Timeout**: Execution timeout
        
            {
                "code": "string",
                "message": "string"
            }
        
*   **Authentication**: Required \[[TypeDB | Docs > Reference > Ty...](https://typedb.com/docs/reference/typedb-http-api/)\]

One-shot Query
--------------

### POST /v1/query

*   **Description**: Run a one-shot query. This endpoint executes a query within a temporary transaction that is opened and then either committed or closed exclusively for this query.
*   **Parameters**:
    *   **Request Body**:
        
            {
                "databaseName": "string",
                "transactionType": "read" | "write" | "schema",
                "query": "string",
                "commit": "boolean",
                "transactionOptions": {
                    "schemaLockAcquireTimeoutMillis": "integer",
                    "transactionTimeoutMillis": "integer"
                },
                "queryOptions": {
                    "includeInstanceTypes": "boolean",
                    "answerCountLimit": "integer"
                }
            }
        
        databaseName, transactionType, and query are required. Other fields are optional.
    *   **Headers**: Authorization: Bearer ACCESS\_TOKEN
*   **Request Format**: JSON in request body
*   **Response Format**:
    *   **200 OK**:
        
            {
                "queryType": "read" | "write" | "schema",
                "answerType": "ok" | "conceptRows" | "conceptDocuments",
                "answers": [],
                "warning": "string"
            }
        
*   **Errors**:
    *   **400 Bad Request**: Incorrectly formatted request
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **403 Forbidden**: Token lacks required access level
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **404 Not Found**: Database not found
        
            {
                "code": "string",
                "message": "string"
            }
        
    *   **408 Request Timeout**: Execution timeout
        
            {
                "code": "string",
                "message": "string"
            }
        
*   **Authentication**: Required \[[TypeDB | Docs > Reference > Ty...](https://typedb.com/docs/reference/typedb-http-api/)\]

_Research completed in 32s - 1 sources_