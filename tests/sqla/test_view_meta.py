import enum

import pytest
import sqlalchemy_file
from sqlalchemy import (
    ARRAY,
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    TypeDecorator,
)
from sqlalchemy.orm import declarative_base, relationship
from starlette_admin import (
    BooleanField,
    DateField,
    DateTimeField,
    DecimalField,
    EnumField,
    FileField,
    HasMany,
    HasOne,
    ImageField,
    IntegerField,
    JSONField,
    StringField,
    TagsField,
    TextAreaField,
    TimeField,
)
from starlette_admin.contrib.sqla.exceptions import (
    InvalidModelError,
    NotSupportedColumn,
)
from starlette_admin.contrib.sqla.view import ModelView

Base = declarative_base()


class Status(str, enum.Enum):
    NEW = "new"
    ONGOING = "ongoing"
    DONE = "done"


class User(Base):
    __tablename__ = "user"

    name = Column(String(100), primary_key=True)
    bio = Column(Text)
    document = relationship("Document", back_populates="user", uselist=False)


class Attachment(Base):
    __tablename__ = "attachment"

    id = Column(Integer, primary_key=True)
    image = Column(sqlalchemy_file.ImageField)
    images = Column(sqlalchemy_file.ImageField(multiple=True))
    file = Column(sqlalchemy_file.FileField)
    files = Column(sqlalchemy_file.FileField(multiple=True))
    document_id = Column(Integer, ForeignKey("document.int"))
    document = relationship("Document", back_populates="attachments")


class Document(Base):
    __tablename__ = "document"

    int = Column(Integer, primary_key=True)
    float = Column(Float)
    bool = Column(Boolean)
    datetime = Column(DateTime)
    date = Column(Date)
    time = Column(Time)
    enum = Column(Enum(Status))
    json_field = Column(JSON)
    tags = Column(ARRAY(String, dimensions=1))
    user_name = Column(String(100), ForeignKey("user.name"))
    user = relationship("User", back_populates="document")
    attachments = relationship("Attachment", back_populates="document")


class UserView(ModelView, model=User):
    form_include_pk = True


class AttachmentView(ModelView, model=Attachment):
    pass


class DocumentView(ModelView, model=Document):
    pass


def test_fields_conversion():
    assert UserView.identity == "user"
    assert AttachmentView.identity == "attachment"
    assert DocumentView.identity == "document"
    assert UserView().fields == [
        StringField("name", required=True),
        TextAreaField("bio"),
        HasOne("document", identity="document", orderable=False, searchable=False),
    ]
    assert AttachmentView().fields == [
        IntegerField(
            "id", required=True, exclude_from_create=True, exclude_from_edit=True
        ),
        ImageField("image", orderable=False, searchable=False),
        ImageField("images", multiple=True, orderable=False, searchable=False),
        FileField("file", orderable=False, searchable=False),
        FileField("files", multiple=True, orderable=False, searchable=False),
        HasOne("document", identity="document", orderable=False, searchable=False),
    ]
    assert DocumentView().fields == [
        IntegerField(
            "int", required=True, exclude_from_create=True, exclude_from_edit=True
        ),
        DecimalField("float"),
        BooleanField("bool"),
        DateTimeField("datetime"),
        DateField("date"),
        TimeField("time"),
        EnumField.from_enum("enum", Status),
        JSONField("json_field"),
        TagsField("tags"),
        HasOne("user", identity="user", orderable=False, searchable=False),
        HasMany(
            "attachments", identity="attachment", orderable=False, searchable=False
        ),
    ]


def test_not_supported_array_columns():
    with pytest.raises(
        NotSupportedColumn, match="Column ARRAY with dimensions != 1 is not supported"
    ):

        class Doc(Base):
            __tablename__ = "doc"
            id = Column(Integer, primary_key=True)
            field = Column(ARRAY(String, dimensions=2))

        class DocView(ModelView, model=Doc):
            pass


def test_fields_customisation():
    class CustomDocumentView(ModelView, model=Document):
        fields = [
            "int",
            Document.bool,
            DecimalField("float", required=True),
            "datetime",
        ]
        exclude_fields_from_create = [Document.datetime]
        exclude_fields_from_detail = ["bool"]
        exclude_fields_from_edit = ["float"]

    assert CustomDocumentView().fields == [
        IntegerField(
            "int", required=True, exclude_from_create=True, exclude_from_edit=True
        ),
        BooleanField("bool", exclude_from_detail=True),
        DecimalField("float", required=True, exclude_from_edit=True),
        DateTimeField("datetime", exclude_from_create=True),
    ]


def test_invalid_field_list():
    with pytest.raises(ValueError, match="Can't find column with key 1"):

        class CustomDocumentView(ModelView, model=Document):
            fields = [1]


def test_invalid_exclude_list():
    with pytest.raises(
        ValueError, match="Expected str or InstrumentedAttribute, got int"
    ):

        class CustomDocumentView(ModelView, model=Document):
            exclude_fields_from_create = [1]


def test_invalid_model():
    with pytest.raises(
        InvalidModelError, match="Class CustomModel is not a SQLAlchemy model"
    ):

        class CustomModel:
            id = Column(Integer, primary_key=True)

        class CustomModelView(ModelView, model=CustomModel):
            pass


def test_conversion_when_impl_callable() -> None:
    class CustomString(TypeDecorator):
        impl = String

    class CustomModel(Base):
        __tablename__ = "impl_callable"

        id = Column(Integer, primary_key=True)
        name = Column(CustomString)

    class CustomModelView(ModelView, model=CustomModel):
        pass

    assert CustomModelView().fields == [
        IntegerField(
            "id", required=True, exclude_from_create=True, exclude_from_edit=True
        ),
        StringField("name"),
    ]


def test_conversion_when_impl_not_callable() -> None:
    class CustomString(TypeDecorator):
        impl = String(length=100)

    class CustomModel(Base):
        __tablename__ = "impl_non_callable"

        id = Column(Integer, primary_key=True)
        name = Column(CustomString)

    class CustomModelView(ModelView, model=CustomModel):
        pass

    assert CustomModelView().fields == [
        IntegerField(
            "id", required=True, exclude_from_create=True, exclude_from_edit=True
        ),
        StringField("name"),
    ]