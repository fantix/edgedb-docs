import contextlib
import os.path
import subprocess
import tempfile
import textwrap
import unittest

import requests_xml


class BuildFailedError(Exception):
    pass


class BaseDomainTest:

    def build(self, src, *, format='html'):
        src = textwrap.dedent(src)

        with tempfile.TemporaryDirectory() as td_in, \
                tempfile.TemporaryDirectory() as td_out:

            fn = os.path.join(td_in, 'contents.rst')
            with open(fn, 'wt') as f:
                f.write(src)
                f.flush()

            args = [
                'sphinx-build',
                '-b', format,
                '-W',
                '-n',
                '-C',
                '-D', 'extensions=edgedb.sphinxext',
                '-q',
                td_in,
                td_out,
                fn
            ]

            try:
                subprocess.run(
                    args, check=True,
                    stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            except subprocess.CalledProcessError as ex:
                msg = [
                    'The build has failed.',
                    '',
                    'STDOUT',
                    '======',
                    ex.stdout.decode(),
                    '',
                    'STDERR',
                    '======',
                    ex.stderr.decode(),
                    '',
                    'INPUT',
                    '=====',
                    src
                ]
                new_ex = BuildFailedError('\n'.join(msg))
                new_ex.stdout = ex.stdout.decode()
                new_ex.stderr = ex.stderr.decode()
                raise new_ex from ex

            with open(os.path.join(td_out, f'contents.{format}'), 'rt') as f:
                out = f.read()

            return out

    @contextlib.contextmanager
    def assert_fails(self, err):
        with self.assertRaises(BuildFailedError) as raised:
            yield

        self.assertRegex(raised.exception.stderr, err)


class TestEqlType(unittest.TestCase, BaseDomainTest):

    def test_eql_type_1(self):
        src = '''
        .. eql:type:: int

            descr
        '''

        out = self.build(src, format='xml')
        x = requests_xml.XML(xml=out)

        self.assertEqual(
            x.xpath('''
                //desc_signature
                    [@eql-fullname="std::int"] /
                    desc_name / text()
            '''),
            ['int'])

    def test_eql_type_2(self):
        src = '''
        .. eql:type:: std::int
        '''

        with self.assert_fails('the directive must include a description'):
            self.build(src)

    def test_eql_type_3(self):
        src = '''
        .. eql:type:: std::int

            aaa

        Testing refs :eql:type:`int1`
        '''

        with self.assert_fails(
                "cannot resolve :eql:type: targeting 'type::std::int1'"):
            self.build(src)

    def test_eql_type_4(self):
        src = '''
        .. eql:type:: std::int

            aaa

        Testing refs :eql:type:`int`
        '''

        self.assertRegex(
            self.build(src),
            r'(?x).*<a .* href="#std::int".*')

    def test_eql_type_5(self):
        src = '''
        .. eql:type:: std::int

            long text long text long text long text long text long text
            long text long text long text long text long text long text

            long text
        '''

        with self.assert_fails("shorter than 80 characters"):
            self.build(src)

    def test_eql_type_6(self):
        src = '''
        .. eql:type:: std::int

            An integer.

        .. eql:type:: std::array

            Array.

        Testing :eql:type:`XXX <array<int>>` ref.
        Testing :eql:type:`array\<int\>` ref.
        Testing :eql:type:`array\<int64\> <array<int>>` ref.
        Testing :eql:type:`array\<array\<int\>\>` ref.
        '''

        out = self.build(src, format='xml')
        x = requests_xml.XML(xml=out)

        self.assertEqual(
            x.xpath('''
                //paragraph /
                reference[@eql-type="type"] /
                literal / text()
            '''),
            ['XXX', 'array<int>', 'array<int64>', 'array<array<int>>'])

    def test_eql_type_7(self):
        src = '''
        .. eql:type:: int

            An integer.

        Testing :eql:type:`OPTIONAL  int` ref.
        Testing :eql:type:`OPTIONAL int` ref.
        Testing :eql:type:`SET  OF  int` ref.
        Testing :eql:type:`SET OF int` ref.
        '''

        out = self.build(src, format='xml')
        x = requests_xml.XML(xml=out)

        self.assertEqual(
            x.xpath('''
                //paragraph /
                reference[@eql-type="type"] /
                literal / text()
            '''),
            ['OPTIONAL  int', 'OPTIONAL int', 'SET  OF  int', 'SET OF int'])

    def test_eql_type_8(self):
        src = '''
        .. eql:type:: SET OF

            An integer.

        Testing :eql:type:`SET OF`.
        Testing :eql:type:`XXX <SET OF>`.
        '''

        out = self.build(src, format='xml')
        x = requests_xml.XML(xml=out)

        self.assertEqual(
            x.xpath('''
                //paragraph /
                reference[@eql-type="type"] /
                literal / text()
            '''),
            ['SET OF', 'XXX'])


class TestEqlFunction(unittest.TestCase, BaseDomainTest):

    def test_eql_func_1(self):
        src = '''
        .. eql:type:: std::int

            An integer.

        .. eql:type:: any

            any.

        .. eql:function:: std::test(any) -> any

            :param $0: param
            :paramtype $0: int

            :return: something
            :returntype: any

            blah

        Testing :eql:func:`XXX <test>` ref.
        Testing :eql:func:`test` ref.
        '''

        out = self.build(src, format='xml')
        x = requests_xml.XML(xml=out)

        func = x.xpath('//desc[@desctype="function"]')
        self.assertEqual(len(func), 1)
        func = func[0]
        param, ret = func.xpath('//field')

        self.assertEqual(func.attrs['summary'], 'blah')

        self.assertEqual(
            param.attrs,
            {'eql-name': 'parameter', 'eql-paramname': '$0',
             'eql-paramtype': 'int'})

        self.assertEqual(
            ret.attrs,
            {'eql-name': 'return', 'eql-paramname': '',
             'eql-paramtype': 'any'})

        self.assertEqual(
            param.xpath('''
                //reference[@eql-type="type" and @refid="type::std::int"] /
                    literal_emphasis/text()
            '''),
            ['int'])

        self.assertEqual(
            x.xpath('''
                //paragraph /
                reference[@eql-type="function" and
                    @refid="function::std::test"] /
                literal / text()
            '''),
            ['XXX', 'test()'])

    def test_eql_func_2(self):
        src = '''
        .. eql:function:: std::test() -> any

            :return: something
            :returntype: any

            long text long text long text long text long text long text
            long text long text long text long text long text long text

            long text
        '''

        with self.assert_fails("shorter than 80 characters"):
            self.build(src)

    def test_eql_func_3(self):
        src = '''
        .. eql:function:: std::test(any) -> any

            :param $0: aaaa
            :type $0: int

            blah
        '''

        expected = r'''(?xs)
        found\sunknown\sfield\s'type' .*
        Possible\sreason:\sfield\s'type'\sis\snot\ssupported
        '''

        with self.assert_fails(expected):
            self.build(src)

    def test_eql_func_4(self):
        src = '''
        .. eql:function:: std::test(any) -> any

            :param $0: aaaa
            :paramtype: int

            blah
        '''

        expected = r'''(?xs)
        found\sunknown\sfield\s'paramtype' .*
        Possible\sreason:\sfield\s'paramtype'\sis\snot\ssupported
        '''

        with self.assert_fails(expected):
            self.build(src)

    def test_eql_func_5(self):
        src = '''
        .. eql:function:: std::test(any) -> any

            :param $0: aaaa
            :paramtype $0: int

        blah
        '''

        with self.assert_fails('the directive must include a description'):
            self.build(src)

    def test_eql_func_6(self):
        src = '''
        .. eql:function:: std::test(any) -> any

            blah

            :param $0: aaaa
            :paramtype $0: int

            blah
        '''

        with self.assert_fails(
                'fields must be specified before all other content'):
            self.build(src)

    def test_eql_func_7(self):
        src = '''
        .. eql:function:: std::test(OPTIONAL str, SET OF str, str) \\
                            -> SET OF str

            blah

        '''

        out = self.build(src, format='xml')
        x = requests_xml.XML(xml=out)

        self.assertEqual(
            x.xpath('//desc_parameter / text()'),
            ['OPTIONAL str', 'SET OF str', 'str'])

        self.assertEqual(
            x.xpath('//desc_returns / text()'),
            ['SET OF str'])

        self.assertEqual(
            x.xpath('//desc_signature/@eql-signature'),
            ['std::test(OPTIONAL str, SET OF str, str) -> SET OF str'])


class TestEqlConstraint(unittest.TestCase, BaseDomainTest):

    def test_eql_constr_1(self):
        src = '''
        .. eql:type:: std::int

            An integer.

        .. eql:type:: any

            any.

        .. eql:constraint:: std::maxlength(any)

            :param $0: param
            :paramtype $0: any

            blah

        Testing :eql:constraint:`XXX <maxlength>` ref.
        Testing :eql:constraint:`maxlength` ref.
        '''

        out = self.build(src, format='xml')
        x = requests_xml.XML(xml=out)

        constr = x.xpath('//desc[@desctype="constraint"]')
        self.assertEqual(len(constr), 1)
        constr = constr[0]
        param, = constr.xpath('//field')

        self.assertEqual(constr.attrs['summary'], 'blah')

        self.assertEqual(
            param.attrs,
            {'eql-name': 'parameter', 'eql-paramname': '$0',
             'eql-paramtype': 'any'})

        self.assertEqual(
            param.xpath('''
                //reference[@eql-type="type" and @refid="type::std::any"] /
                    literal_emphasis/text()
            '''),
            ['any'])

        self.assertEqual(
            x.xpath('''
                //paragraph /
                reference[@eql-type="constraint" and
                    @refid="constraint::std::maxlength"] /
                literal / text()
            '''),
            ['XXX', 'maxlength'])

    def test_eql_constr_2(self):
        src = '''
        .. eql:constraint:: std::length on (len(<std::str>__subject__))

            blah
        '''

        out = self.build(src, format='xml')
        x = requests_xml.XML(xml=out)

        constr = x.xpath('//desc[@desctype="constraint"]')
        self.assertEqual(len(constr), 1)
        constr = constr[0]
        sig = constr.xpath('//desc_signature')[0]

        self.assertEqual(
            sig.xpath('@eql-signature'),
            ['std::length ON (len(<std::str>__subject__))'])

        self.assertEqual(
            sig.xpath('@eql-subjexpr'),
            ['len(<std::str>__subject__)'])


class TestEqlOperator(unittest.TestCase, BaseDomainTest):

    def test_eql_op_1(self):
        src = '''
        .. eql:type:: int

            int

        .. eql:type:: str

            123

        .. eql:operator:: PLUS: A + B

            :optype A: int or str
            :optype B: int or str
            :resulttype: int or str

            Arithmetic addition.

        some text

        :eql:op:`XXX <PLUS>`
        '''

        out = self.build(src, format='xml')
        x = requests_xml.XML(xml=out)

        self.assertEqual(
            len(x.xpath('''
                //desc_signature[@eql-name="PLUS" and @eql-signature="A + B"] /
                *[
                    (self::desc_annotation and text()="operator") or
                    (self::desc_name and text()="A + B")
                ]
            ''')),
            2)

        self.assertEqual(len(x.xpath('//field[@eql-name="operand"]')), 2)
        self.assertEqual(len(x.xpath('//field[@eql-name="resulttype"]')), 1)

        self.assertEqual(
            x.xpath('''
                //paragraph /
                reference[@eql-type="operator" and @refid="operator::PLUS"] /
                literal / text()
            '''),
            ['XXX'])

    def test_eql_op_2(self):
        src = '''
        .. eql:type:: any

            123

        .. eql:operator:: IS: A IS B

            :optype A: any
            :optype B: type
            :resulttype: any

            Is

        :eql:op:`XXX <IS>`
        '''

        out = self.build(src, format='xml')
        x = requests_xml.XML(xml=out)

        self.assertEqual(
            x.xpath('''
                //field[@eql-opname="B"] /
                field_body / * / literal_strong / text()
            '''),
            ['B'])


class TestEqlKeyword(unittest.TestCase, BaseDomainTest):

    def test_eql_kw_1(self):
        src = '''
        .. eql:keyword:: SET OF

            blah

        some text

        :eql:kw:`XXX <SET OF>`
        '''

        out = self.build(src, format='xml')
        x = requests_xml.XML(xml=out)

        self.assertEqual(
            len(x.xpath('''
                //desc[@desctype="keyword"] /

                desc_signature[@eql-name="SET OF"] /
                *[
                    (self::desc_annotation and text()="keyword") or
                    (self::desc_name and text()="SET OF")
                ]
            ''')),
            2)

        self.assertEqual(
            x.xpath('''
                //paragraph /
                reference[@eql-type="keyword" and @refid="keyword::SET-OF"] /
                literal / text()
            '''),
            ['XXX'])


class TestEqlStatement(unittest.TestCase, BaseDomainTest):

    def test_eql_stmt_5(self):
        src = '''

        CREATE FUNCTION
        ===============

        :eql-statement:

        Creates a function.

        Subhead
        -------

        asdasdas


        CREATE TYPE
        ===========

        :eql-statement:

        blah.


        Test
        ====

        A ref to :eql:stmt:`CREATE FUNCTION`

        A ref to :eql:stmt:`ttt <CREATE TYPE>`
        '''

        out = self.build(src, format='xml')
        x = requests_xml.XML(xml=out)

        self.assertEqual(
            x.xpath('''
                //paragraph /
                reference[@eql-type="statement" and
                          @refid="statement::CREATE-FUNCTION"] /
                literal / text()
            '''),
            ['CREATE FUNCTION'])

        self.assertEqual(
            x.xpath('''
                //paragraph /
                reference[@eql-type="statement" and
                          @refid="statement::CREATE-TYPE"] /
                literal / text()
            '''),
            ['ttt'])

        self.assertEqual(
            x.xpath('''
                //section[@eql-statement="true"]/@ids
            '''),
            ['create-function statement::CREATE-FUNCTION',
             'create-type statement::CREATE-TYPE'])

    def test_eql_stmt_6(self):
        src = '''

        AAAAAA
        ======

        :eql-statement:

        aa aaaaaa aaaaa aaaa aa aaaaaa aaaaa aaaa aa aaaaaa aaaaa aaaa aa
        aa aaaaaa aaaaa aaaa aa aaaaaa aaaaa aaaa.
        '''

        with self.assert_fails(
                'first paragraph is longer than 79 characters'):
            self.build(src)

    def test_eql_stmt_7(self):
        src = '''

        AA aa
        =====

        :eql-statement:

        aa aaaaaa aaaaa aaaa aa.

        aa aaaaaa aaaaa aaaa aa aaaaaa aaaaa aaaa.
        '''

        with self.assert_fails(
                'but does not satisfy pattern for valid'):
            self.build(src)

    def test_eql_stmt_8(self):
        src = '''

        AA AA
        =====

        :eql-statement:

        aa aaaaaa aaaaa aaaa aa.

        BB
        --

        :eql-statement:

        bbb.
        '''

        with self.assert_fails(
                ' has a nested section with a :eql-statement:'):
            self.build(src)

    def test_eql_stmt_9(self):
        src = '''

        AA AA
        =====

        :eql-statement:

        aa aaaaaa aaaaa aaaa aa.

        AA AA
        =====

        :eql-statement:

        aa aaaaaa aaaaa aaaa aa.
        '''

        with self.assert_fails("duplicate 'AA AA' statement"):
            self.build(src)

    def test_eql_stmt_10(self):
        src = '''
        =========
        Functions
        =========

        This section describes the DDL commands ...


        CREATE FUNCTION
        ===============

        :eql-statement:

        Define a new function.


        DROP FUNCTION
        =============

        :eql-statement:
        :eql-haswith:

        Remove a function.
        '''

        out = self.build(src, format='xml')
        x = requests_xml.XML(xml=out)

        self.assertEqual(
            x.xpath('''
                //section[@eql-statement="true"]/title/text()
            '''),
            ['CREATE FUNCTION', 'DROP FUNCTION'])

        self.assertEqual(
            x.xpath('''
                //section[@eql-statement="true" and @eql-haswith="true"]
                    /title/text()
            '''),
            ['DROP FUNCTION'])


class TestEqlInlineCode(unittest.TestCase, BaseDomainTest):

    def test_eql_inline_role_1(self):
        src = '''
        a test of :eql:synopsis:`WITH <aaaa>`.
        '''

        out = self.build(src, format='xml')
        x = requests_xml.XML(xml=out)

        self.assertEqual(
            x.xpath('''
                //literal[@eql-lang="edgeql-synopsis"] / text()
            '''),
            ['WITH <aaaa>'])


class TestBlockquote(unittest.TestCase, BaseDomainTest):

    def test_eql_blockquote_1(self):
        src = '''
        blah

         * list
         * item
        '''

        with self.assert_fails('block_quote found'):
            self.build(src, format='xml')

        with self.assert_fails('block_quote found'):
            self.build(src, format='html')
