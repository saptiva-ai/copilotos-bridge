"""
E2E Tests: Registry Configuration and Integration

Verifica que el registry.yaml se cargue correctamente
y que la configuración se aplique en toda la aplicación.
"""

import pytest
from apps.api.src.core.prompt_registry import (
    get_prompt_registry,
    ModelParams,
    PromptEntry
)


class TestRegistryConfiguration:
    """Tests para verificar configuración del registry"""

    def test_registry_singleton_pattern(self):
        """
        Verificar que get_prompt_registry retorne la misma instancia
        """
        registry1 = get_prompt_registry()
        registry2 = get_prompt_registry()

        assert registry1 is registry2, "Debe retornar la misma instancia (singleton)"

    def test_all_expected_models_loaded(self):
        """
        Verificar que todos los modelos esperados estén cargados
        """
        registry = get_prompt_registry()

        expected_models = {
            "default",
            "Saptiva Turbo",
            "Saptiva Cortex",
            "Saptiva Ops",
            "Saptiva Coder"
        }

        loaded_models = set(registry.get_available_models())

        assert expected_models.issubset(loaded_models), \
            f"Falta algún modelo esperado. Cargados: {loaded_models}"

    def test_each_model_has_valid_params(self):
        """
        Verificar que cada modelo tenga parámetros válidos
        """
        registry = get_prompt_registry()

        for model_name in registry.get_available_models():
            entry = registry.models[model_name]

            # Verificar que params existan y sean válidos
            assert entry.params is not None
            assert isinstance(entry.params, ModelParams)

            # Verificar rangos de parámetros
            assert 0.0 <= entry.params.temperature <= 2.0
            assert 0.0 <= entry.params.top_p <= 1.0
            assert -2.0 <= entry.params.presence_penalty <= 2.0
            assert -2.0 <= entry.params.frequency_penalty <= 2.0

    def test_cortex_has_higher_temperature_than_ops(self):
        """
        Verificar que Cortex (análisis) tenga temperatura mayor que Ops (código)
        """
        registry = get_prompt_registry()

        cortex = registry.models["Saptiva Cortex"]
        ops = registry.models["Saptiva Ops"]

        assert cortex.params.temperature > ops.params.temperature, \
            "Cortex debería ser más creativo que Ops"

    def test_turbo_has_lowest_temperature(self):
        """
        Verificar que Turbo tenga la temperatura más baja (más determinista)
        """
        registry = get_prompt_registry()

        turbo = registry.models["Saptiva Turbo"]

        # Turbo debería tener temperatura baja para velocidad y consistencia
        assert turbo.params.temperature <= 0.3, \
            "Turbo debería tener temperatura baja para determinismo"


class TestPromptPlaceholderSubstitution:
    """Tests para verificar sustitución de placeholders"""

    def test_copilot_name_substitution(self):
        """
        Verificar que {CopilotOS} se sustituya correctamente
        """
        registry = get_prompt_registry()

        system_text, _ = registry.resolve("default", channel="chat")

        assert "{CopilotOS}" not in system_text, \
            "Placeholder {CopilotOS} no debe estar presente"
        assert registry.copilot_name in system_text, \
            f"Debe contener el copilot_name: {registry.copilot_name}"

    def test_org_name_substitution(self):
        """
        Verificar que {Saptiva} se sustituya correctamente
        """
        registry = get_prompt_registry()

        system_text, _ = registry.resolve("default", channel="chat")

        assert "{Saptiva}" not in system_text, \
            "Placeholder {Saptiva} no debe estar presente"
        assert registry.org_name in system_text, \
            f"Debe contener el org_name: {registry.org_name}"

    def test_tools_placeholder_removed_when_no_tools(self):
        """
        Verificar que {TOOLS} se remueva cuando no hay herramientas
        """
        registry = get_prompt_registry()

        system_text, _ = registry.resolve("default", tools_markdown=None, channel="chat")

        assert "{TOOLS}" not in system_text, \
            "Placeholder {TOOLS} no debe estar presente sin herramientas"

    def test_tools_placeholder_replaced_when_tools_provided(self):
        """
        Verificar que {TOOLS} se reemplace con markdown de herramientas
        """
        registry = get_prompt_registry()

        tools_md = "* **search** — Search the web\n* **calc** — Calculate"
        system_text, _ = registry.resolve("default", tools_markdown=tools_md, channel="chat")

        assert "{TOOLS}" not in system_text, \
            "Placeholder {TOOLS} no debe estar presente"
        assert "search" in system_text, \
            "Debe contener la descripción de la herramienta search"
        assert "calc" in system_text, \
            "Debe contener la descripción de la herramienta calc"


class TestAddendumInjection:
    """Tests para verificar inyección de addendums"""

    def test_cortex_addendum_present(self):
        """
        Verificar que Cortex incluya su addendum específico
        """
        registry = get_prompt_registry()

        entry = registry.models["Saptiva Cortex"]
        system_text, _ = registry.resolve("Saptiva Cortex", channel="chat")

        assert entry.addendum is not None, \
            "Cortex debe tener addendum"
        assert "Optimización Cortex" in system_text, \
            "Debe incluir el addendum de Cortex"
        assert "rigor" in system_text.lower(), \
            "Addendum de Cortex debe mencionar rigor"

    def test_turbo_addendum_present(self):
        """
        Verificar que Turbo incluya su addendum de optimización
        """
        registry = get_prompt_registry()

        entry = registry.models["Saptiva Turbo"]
        system_text, _ = registry.resolve("Saptiva Turbo", channel="chat")

        assert entry.addendum is not None, \
            "Turbo debe tener addendum"
        assert "Optimización Turbo" in system_text, \
            "Debe incluir el addendum de Turbo"
        assert "brevedad" in system_text.lower() or "velocidad" in system_text.lower(), \
            "Addendum de Turbo debe mencionar brevedad o velocidad"

    def test_ops_addendum_present(self):
        """
        Verificar que Ops incluya su addendum de código
        """
        registry = get_prompt_registry()

        entry = registry.models["Saptiva Ops"]
        system_text, _ = registry.resolve("Saptiva Ops", channel="chat")

        assert entry.addendum is not None, \
            "Ops debe tener addendum"
        assert "Optimización Ops" in system_text, \
            "Debe incluir el addendum de Ops"
        assert "código" in system_text.lower() or "devops" in system_text.lower(), \
            "Addendum de Ops debe mencionar código o DevOps"

    def test_default_model_no_addendum(self):
        """
        Verificar que el modelo default no tenga addendum
        (es genérico/agnóstico)
        """
        registry = get_prompt_registry()

        entry = registry.models["default"]

        assert entry.addendum is None, \
            "Default no debe tener addendum (es genérico)"


class TestChannelMaxTokensConfiguration:
    """Tests para verificar max_tokens por canal"""

    def test_chat_channel_limit(self):
        """
        Verificar límite de tokens para canal 'chat'
        """
        registry = get_prompt_registry()

        _, params = registry.resolve("default", channel="chat")

        assert params["max_tokens"] == 1200, \
            "Canal 'chat' debe tener max_tokens=1200"

    def test_report_channel_limit(self):
        """
        Verificar límite de tokens para canal 'report'
        """
        registry = get_prompt_registry()

        _, params = registry.resolve("default", channel="report")

        assert params["max_tokens"] == 3500, \
            "Canal 'report' debe tener max_tokens=3500"

    def test_title_channel_limit(self):
        """
        Verificar límite de tokens para canal 'title'
        """
        registry = get_prompt_registry()

        _, params = registry.resolve("default", channel="title")

        assert params["max_tokens"] == 64, \
            "Canal 'title' debe tener max_tokens=64"

    def test_summary_channel_limit(self):
        """
        Verificar límite de tokens para canal 'summary'
        """
        registry = get_prompt_registry()

        _, params = registry.resolve("default", channel="summary")

        assert params["max_tokens"] == 256, \
            "Canal 'summary' debe tener max_tokens=256"

    def test_code_channel_limit(self):
        """
        Verificar límite de tokens para canal 'code'
        """
        registry = get_prompt_registry()

        _, params = registry.resolve("default", channel="code")

        assert params["max_tokens"] == 2048, \
            "Canal 'code' debe tener max_tokens=2048"


class TestSystemPromptHashing:
    """Tests para verificar hashing de system prompts"""

    def test_same_model_generates_consistent_hash(self):
        """
        Verificar que el mismo modelo genere el mismo hash (determinista)
        """
        registry = get_prompt_registry()

        _, params1 = registry.resolve("Saptiva Cortex", channel="chat")
        _, params2 = registry.resolve("Saptiva Cortex", channel="chat")

        hash1 = params1["_metadata"]["system_hash"]
        hash2 = params2["_metadata"]["system_hash"]

        assert hash1 == hash2, \
            "El mismo modelo debe generar el mismo hash"

    def test_different_models_generate_different_hashes(self):
        """
        Verificar que modelos diferentes generen hashes diferentes
        """
        registry = get_prompt_registry()

        _, params_cortex = registry.resolve("Saptiva Cortex", channel="chat")
        _, params_turbo = registry.resolve("Saptiva Turbo", channel="chat")

        hash_cortex = params_cortex["_metadata"]["system_hash"]
        hash_turbo = params_turbo["_metadata"]["system_hash"]

        assert hash_cortex != hash_turbo, \
            "Modelos diferentes deben generar hashes diferentes"

    def test_same_model_different_tools_generates_different_hash(self):
        """
        Verificar que diferentes herramientas cambien el hash
        (porque cambia el system prompt)
        """
        registry = get_prompt_registry()

        _, params_no_tools = registry.resolve(
            "Saptiva Cortex",
            tools_markdown=None,
            channel="chat"
        )

        _, params_with_tools = registry.resolve(
            "Saptiva Cortex",
            tools_markdown="* **search** — Search",
            channel="chat"
        )

        hash_no_tools = params_no_tools["_metadata"]["system_hash"]
        hash_with_tools = params_with_tools["_metadata"]["system_hash"]

        assert hash_no_tools != hash_with_tools, \
            "Diferentes herramientas deben generar hashes diferentes"

    def test_hash_format_is_valid(self):
        """
        Verificar que el hash tenga formato válido (16 chars hex)
        """
        registry = get_prompt_registry()

        _, params = registry.resolve("Saptiva Cortex", channel="chat")
        hash_value = params["_metadata"]["system_hash"]

        assert isinstance(hash_value, str), \
            "Hash debe ser string"
        assert len(hash_value) == 16, \
            "Hash debe tener 16 caracteres (primeros 16 de SHA256)"
        assert all(c in "0123456789abcdef" for c in hash_value), \
            "Hash debe ser hexadecimal"


class TestMetadataInjection:
    """Tests para verificar metadata inyectada en params"""

    def test_metadata_includes_model_name(self):
        """
        Verificar que metadata incluya el nombre del modelo
        """
        registry = get_prompt_registry()

        _, params = registry.resolve("Saptiva Cortex", channel="chat")

        assert "_metadata" in params
        assert params["_metadata"]["model"] == "Saptiva Cortex"

    def test_metadata_includes_channel(self):
        """
        Verificar que metadata incluya el canal
        """
        registry = get_prompt_registry()

        _, params = registry.resolve("Saptiva Cortex", channel="report")

        assert params["_metadata"]["channel"] == "report"

    def test_metadata_includes_addendum_flag(self):
        """
        Verificar que metadata indique si hay addendum
        """
        registry = get_prompt_registry()

        _, params_cortex = registry.resolve("Saptiva Cortex", channel="chat")
        _, params_default = registry.resolve("default", channel="chat")

        assert params_cortex["_metadata"]["has_addendum"] is True
        assert params_default["_metadata"]["has_addendum"] is False

    def test_metadata_includes_version(self):
        """
        Verificar que metadata incluya la versión del registry
        """
        registry = get_prompt_registry()

        _, params = registry.resolve("Saptiva Cortex", channel="chat")

        assert "version" in params["_metadata"]
        assert params["_metadata"]["version"] == registry.version
