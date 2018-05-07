:orphan:

.. _ref_eql_expr_shapes:

======
Shapes
======

A *shape* is a powerful syntactic construct that can be used to dynamically
describe a portion of an object graph.  Shapes are used to describe
``views``, ``insert`` and ``update`` data and to specify the format of
statement output.

Shapes always follow an expression, and are a list of *shape elements*
enclosed in curly braces:

.. eql:synopsis::

    <expr> "{"
        <shape_element> [, ...]
    "}"


Shape element has the following syntax:

.. eql:synopsis::

    [ "[" IS <object-type> "]" ] <pointer-spec>

If an optional :eql:synopsis:`<object-type>` filter is used,
:eql:synopsis:`<pointer-spec>` will only apply to those objects in
the :eql:synopsis:`<expr>` set that are instances of
:eql:synopsis:`<object-type>`.

:eql:synopsis:`<pointer-spec>` is one of the following:

- a name of an existing link or property of a type produced
  by :eql:synopsis:`<expr>`;

- a declaration of a computable link or property in the form
  ``[@]<name> := <ptrexpr>``;

- a *subshape* in the form
  :eql:synopsis:`<pointer-name>: [<target-type>] "{" ... "}"`, where
  :eql:synopsis:`<pointer-name>` is the name of an existing link or property,
  and :eql:synopsis:`<target-type>` is an optional object type
  that specifies the type of target objects selected or inserted,
  depending on the context.


.. _ref_eql_expr_shapes_insert:

Shapes in INSERT
================

A shape in an ``INSERT`` statement is used to specify the data to insert
into a database.  The recursive nature of shapes allows creating an entire
tree of objects with a single ``INSERT`` statement.

.. code-block:: edgeql

    INSERT Issue {
        name := 'Issue #1',
        comments: Comment {
            body := 'Issue #1 created'
        }
    };

The above query inserts a new ``Issue`` object, and creates and links a new
``Comment`` object to it.

See :ref:`ref_eql_statements_insert` for more information on the use of
shapes in ``INSERT`` statements.


.. _ref_eql_expr_shapes_update:

Shapes in UPDATE
================

A shape in an ``UPDATE`` statement is used to specify how links and properties
of an object are updated.

.. code-block:: edgeql

    UPDATE Issue
    FILTER Issue.name = 'Issue #1'
    SET
    # Update shape follows
    {
        name := 'Issue #1 (important)',
        comments := Issue.comments UNION (INSERT Comment {
                        body := 'Issue #1 updated'
                    })
    };

The above statement updates the ``name`` property and adds a ``comments`` link
to a new comment for a given ``Issue`` object.

See :ref:`ref_eql_statements_update` for more information on the use of
shapes in ``UPDATE`` statements.


Shapes in Queries
=================

A shape in a ``SELECT`` clause (or the ``UNION`` clause of a
``FOR`` statement) determines the output format for the objects in a set
computed by an expression annotated by the shape.

For example, the below query returns a set of ``Issue`` objects and includes
a ``number`` and an associated owner ``User`` object, which in turn includes
the ``name`` and the ``email`` for that user.

.. code-block:: edgeql-repl

    db> SELECT
    ...     Issue {
    ...         number,
    ...         owner: {  # sub-shape, selects Issue.owner objects
    ...            name,
    ...            email
    ...         }
    ...     };

    {
        'number': 1,
        'owner': {
            'name': 'Alice',
            'email': 'alice@example.com'
        }
    }
