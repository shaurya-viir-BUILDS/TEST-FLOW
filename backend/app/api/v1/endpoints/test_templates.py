from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role, get_current_user
from app.models.product import ProductModel
from app.models.testing import TestTemplate, TestParameter
from app.models.employee import RoleEnum, Employee
from app.schemas.testing import (
    TestTemplateCreate,
    TestTemplateResponse,
    TestTemplateDetailResponse,
    TestParameterResponse
)

router = APIRouter()


def _enrich_template(t: TestTemplate) -> TestTemplateResponse:
    resp = TestTemplateResponse.model_validate(t)
    if t.product_model:
        resp.product_model_number = t.product_model.model_number
        resp.product_model_name = t.product_model.model_name
    resp.parameter_count = len(t.parameters)
    return resp


@router.get("/", response_model=List[TestTemplateResponse])
def list_test_templates(
    product_model_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(get_current_user)
):
    query = db.query(TestTemplate)
    if product_model_id is not None:
        query = query.filter(TestTemplate.product_model_id == product_model_id)
    if is_active is not None:
        query = query.filter(TestTemplate.is_active == is_active)

    templates = query.order_by(TestTemplate.id.desc()).all()
    return [_enrich_template(t) for t in templates]


@router.post("/", response_model=TestTemplateDetailResponse, status_code=status.HTTP_201_CREATED)
def create_test_template(
    template_in: TestTemplateCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_role([RoleEnum.SUPER_ADMIN, RoleEnum.TEST_SUPERVISOR]))
):
    # Verify product model exists
    product = db.query(ProductModel).filter(ProductModel.id == template_in.product_model_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product model not found.")

    template = TestTemplate(
        product_model_id=template_in.product_model_id,
        name=template_in.name.strip(),
        version=template_in.version,
        is_active=template_in.is_active,
        created_by=current_user.id
    )
    db.add(template)
    db.flush()

    for idx, p_in in enumerate(template_in.parameters, start=1):
        param = TestParameter(
            template_id=template.id,
            parameter_name=p_in.parameter_name.strip(),
            data_type=p_in.data_type,
            min_limit=p_in.min_limit,
            max_limit=p_in.max_limit,
            unit_of_measure=p_in.unit_of_measure,
            expected_text=p_in.expected_text.strip() if p_in.expected_text else None,
            is_mandatory=p_in.is_mandatory,
            display_order=p_in.display_order or idx
        )
        db.add(param)

    db.commit()
    db.refresh(template)

    resp = TestTemplateDetailResponse.model_validate(template)
    resp.product_model_number = product.model_number
    resp.product_model_name = product.model_name
    resp.parameter_count = len(template.parameters)
    resp.parameters = [TestParameterResponse.model_validate(p) for p in template.parameters]
    return resp


@router.get("/{id}", response_model=TestTemplateDetailResponse)
def get_test_template(
    id: int,
    db: Session = Depends(get_db),
    _current_user: Employee = Depends(get_current_user)
):
    template = db.query(TestTemplate).filter(TestTemplate.id == id).first()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Template with id {id} not found.")

    resp = TestTemplateDetailResponse.model_validate(template)
    if template.product_model:
        resp.product_model_number = template.product_model.model_number
        resp.product_model_name = template.product_model.model_name
    resp.parameter_count = len(template.parameters)
    resp.parameters = [TestParameterResponse.model_validate(p) for p in template.parameters]
    return resp

