from edgedb.lang.graphql.pygments import GraphQLLexer


def setup_domain(app):
    app.add_lexer("graphql", GraphQLLexer())
