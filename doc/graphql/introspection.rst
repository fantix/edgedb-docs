.. _ref_graphql_introspection:


Introspection
=============

GraphQL introspection can be used to explore the exposed EdgeDB Types
and Views. Note that there are certain types like :eql:type:`tuple` or
:eql:type:`map` that cannot be expressed in terms of GraphQL type system (
a ``tuple`` can be like a heterogeneous "List" and a ``map`` may have
arbitrary "fields").

Consider the following GraphQL introspection query:

.. code-block:: graphql

    {
        __type(name: "Query") {
            name
            fields {
                name
                args {
                    name
                    type {
                        kind
                        name
                    }
                }
            }
        }
    }

Produces:

.. code-block:: json

    {
        "__type": {
            "name": "Query",
            "fields": [
                {
                    "name": "Author",
                    "args": [
                        {
                            "name": "id",
                            "type": {
                                "kind": "SCALAR",
                                "name": "ID"
                            }
                        },
                        {
                            "name": "name",
                            "type": {
                                "kind": "SCALAR",
                                "name": "String"
                            }
                        }
                    ]
                },
                {
                    "name": "Book",
                    "args": [
                        {
                            "name": "id",
                            "type": {
                                "kind": "SCALAR",
                                "name": "ID"
                            }
                        },
                        {
                            "name": "isbn",
                            "type": {
                                "kind": "SCALAR",
                                "name": "String"
                            }
                        },
                        {
                            "name": "synopsis",
                            "type": {
                                "kind": "SCALAR",
                                "name": "String"
                            }
                        },
                        {
                            "name": "title",
                            "type": {
                                "kind": "SCALAR",
                                "name": "String"
                            }
                        }
                    ]
                }
            ]
        }
    }

The above example shows what has been exposed for querying with GraphQL.
