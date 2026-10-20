from enum import IntEnum


class UnifiedGraftModelType(IntEnum):
    LIBRARY = 0
    STATIC_METHOD = 1
    STATIC_FIELD = 2
    CONSTRUCTOR = 3
    TYPE_DEF = 4
    MODULE = 5
    INSTANCE_METHOD = 6
    CAST = 7
    INSTANCE_FIELD = 8
    GLOBAL_METHOD = 9
    DESTRUCTOR = 10
    GENERIC_STATIC_METHOD = 11
    GENERIC_INSTANCE_METHOD = 12
    ENUM = 13
    REF = 14
    OUT = 15
    ARRAY = 16
    PARAMETERS_ARRAY = 17
    ARGUMENT_NAME = 18
    CLASS_NAME = 19
    METHOD_NAME = 20
    MODIFIER = 21
    TYPE_USAGE = 22
    PARAMETER = 23
    NAMESPACE = 24
    MODULE_FULL_NAME = 25
    MODULE_HASH = 26
    METHOD_BODY = 27
    CLAZZ_INSTANCE = 28
    RETURN_TYPE = 29
    GLOBAL_FIELD = 30
    GLOBAL_TYPE = 31
    FIELD_NAME = 32
    PROPERTY = 33
    SETTER = 34
    GETTER = 35
    GENERIC_TYPE_DEF = 36
    OVERLOADED_CONSTRUCTOR = 37
    OVERLOADED_STATIC_METHOD = 38
    OVERLOADED_INSTANCE_METHOD = 39
    OVERLOADED_GLOBAL_METHOD = 40
    TYPE_USAGE_VOID = 41
    TYPE_USAGE_ARRAY = 42
    TYPE_USAGE_PRIMITIVE = 43
    TYPE_USAGE_GENERIC = 44
    TYPE_USAGE_GENERIC_ALIAS = 45
    GENERIC_PARAMETERS = 46
    SET_INSTANCE_FIELD = 47
    SET_STATIC_FIELD = 48
    TYPE_INHERITANCE = 49
    TYPE_INHERITANCE_ENTRY = 50

    # ------------------------------------------------------------------
    # CommentDoc (UGM v1.4.0) - structured documentation comments.
    # See `CommentDoc` spec: a neutral container for Javadoc / XML doc /
    # JSDoc / Python docstring / PHPDoc / YARD-RDoc metadata.
    #
    # COMMENT_DOC is appended at the END of payload of methods/constructors;
    # consumers must look it up by type, not by index, to stay
    # backward-compatible with older payload positional contracts.
    # ------------------------------------------------------------------
    COMMENT_DOC = 51
    COMMENT_SUMMARY = 52
    COMMENT_DESCRIPTION = 53
    COMMENT_PARAMETERS_ARRAY = 54
    COMMENT_PARAMETER = 55
    COMMENT_RETURNS = 56
    COMMENT_THROWS_ARRAY = 57
    COMMENT_THROW = 58
    COMMENT_EXAMPLES_ARRAY = 59
    COMMENT_EXAMPLE = 60
    COMMENT_LINKS_ARRAY = 61
    COMMENT_LINK = 62
    COMMENT_DEPRECATED = 63
    COMMENT_NOTES_ARRAY = 64
    COMMENT_WARNINGS_ARRAY = 65
    COMMENT_METADATA = 66
    COMMENT_SOURCE = 67
    TYPE_DEF_KIND = 68
    ABSTRACT_INSTANCE_METHOD = 69
    ABSTRACT_STATIC_METHOD = 70
    READONLY_SETTER = 71
