"""API routes for model configurations."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from symbology.api.schemas import ModelConfigResponse
from symbology.database.model_configs import (
    get_all_model_configs,
    get_model_config,
    get_model_config_by_name,
)
from symbology.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get(
    "/",
    response_model=List[ModelConfigResponse],
    status_code=status.HTTP_200_OK,
    responses={
        500: {"description": "Internal server error"}
    }
)
async def list_all_model_configs():
    """Get all model configurations.

    Returns:
        List of ModelConfigResponse objects
    """
    logger.info("api_list_all_model_configs")

    try:
        configs = get_all_model_configs()

        # Convert database models to response schemas
        response_data = []
        for config in configs:
            config_dict = config.to_dict()
            # Add computed properties
            config_dict.update({
                'num_ctx': config.num_ctx,
                'temperature': config.temperature,
                'top_k': config.top_k,
                'top_p': config.top_p,
                'seed': config.seed,
                'num_predict': config.num_predict if hasattr(config, 'num_predict') else None,
                'num_gpu': config.num_gpu if hasattr(config, 'num_gpu') else None,
            })
            response_data.append(ModelConfigResponse(**config_dict))

        logger.info("api_list_all_model_configs_success", count=len(response_data))
        return response_data

    except Exception as e:
        logger.error("api_list_all_model_configs_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving model configurations"
        ) from e


@router.get(
    "/{config_id}",
    response_model=ModelConfigResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Model configuration not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_model_config_by_id(config_id: UUID):
    """Get model configuration by its ID.

    Args:
        config_id: UUID of the model configuration

    Returns:
        ModelConfigResponse object with the configuration details
    """
    logger.info("api_get_model_config_by_id", config_id=str(config_id))

    try:
        config = get_model_config(config_id)

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model configuration not found with ID: {config_id}"
            )

        config_dict = config.to_dict()
        # Add computed properties
        config_dict.update({
            'num_ctx': config.num_ctx,
            'temperature': config.temperature,
            'top_k': config.top_k,
            'top_p': config.top_p,
            'seed': config.seed,
            'num_predict': config.num_predict if hasattr(config, 'num_predict') else None,
            'num_gpu': config.num_gpu if hasattr(config, 'num_gpu') else None,
        })
        response = ModelConfigResponse(**config_dict)

        logger.info("api_get_model_config_by_id_success", config_id=str(config_id))
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("api_get_model_config_by_id_failed",
                    config_id=str(config_id), error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving model configuration"
        ) from e


@router.get(
    "/by-name/{model_name}",
    response_model=ModelConfigResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Model configuration not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_model_config_by_model_name(model_name: str):
    """Get model configuration by model name.

    Args:
        model_name: Name of the model (e.g., 'qwen3:14b', 'gemma3:12b')

    Returns:
        ModelConfigResponse object with the configuration details
    """
    logger.info("api_get_model_config_by_name", model_name=model_name)

    try:
        config = get_model_config_by_name(model_name)

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model configuration not found with name: {model_name}"
            )

        config_dict = config.to_dict()
        # Add computed properties
        config_dict.update({
            'num_ctx': config.num_ctx,
            'temperature': config.temperature,
            'top_k': config.top_k,
            'top_p': config.top_p,
            'seed': config.seed,
            'num_predict': config.num_predict if hasattr(config, 'num_predict') else None,
            'num_gpu': config.num_gpu if hasattr(config, 'num_gpu') else None,
        })
        response = ModelConfigResponse(**config_dict)

        logger.info("api_get_model_config_by_name_success", model_name=model_name)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("api_get_model_config_by_name_failed",
                    model_name=model_name, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving model configuration"
        ) from e
