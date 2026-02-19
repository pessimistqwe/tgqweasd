"""
Web3 Configuration Tests

Запуск:
    pytest tests/test_web3_config.py -v

Тест-кейсы:
1. test_web3_config_exists — файл конфигурации существует
2. test_contract_addresses_defined — все 4 контракта имеют адреса
3. test_web3_docs_exist — файлы документации существуют
4. test_contract_addresses_valid_format — адреса валидного формата
5. test_web3_stub_functions — заглушки функций возвращают корректные значения
"""

import pytest
import os
import json
import re


# ===========================================
# Web3 Configuration File Tests
# ===========================================

class TestWeb3ConfigFiles:
    """Tests for Web3 configuration files existence"""

    def test_backend_config_exists(self):
        """test_web3_config_exists — backend config file exists"""
        config_path = os.path.join(os.path.dirname(__file__), '..', 'api', 'config', 'polymarket_contracts.py')
        assert os.path.exists(config_path), f"Backend config not found: {config_path}"
        print("[PASS] test_backend_config_exists")

    def test_frontend_config_exists(self):
        """test_web3_config_exists — frontend config file exists"""
        config_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'web3Config.ts')
        assert os.path.exists(config_path), f"Frontend config not found: {config_path}"
        print("[PASS] test_frontend_config_exists")

    def test_web3_docs_exist(self):
        """test_web3_docs_exist — documentation files exist"""
        docs = [
            os.path.join(os.path.dirname(__file__), '..', 'WEB3_INTEGRATION.md'),
            os.path.join(os.path.dirname(__file__), '..', 'POLYMARKET_COMPATIBILITY.md')
        ]
        for doc_path in docs:
            assert os.path.exists(doc_path), f"Doc not found: {doc_path}"
        print(f"[PASS] test_web3_docs_exist ({len(docs)} files)")


class TestContractAddresses:
    """Tests for contract addresses configuration"""

    def test_contract_addresses_defined(self):
        """test_contract_addresses_defined — all 4 contracts have addresses"""
        # Импортируем конфигурацию
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))
        from config.polymarket_contracts import POLYMARKET_CONTRACTS

        contracts = POLYMARKET_CONTRACTS["contracts"]
        required_contracts = ["USDC_E", "CTF", "CTF_EXCHANGE", "NEG_RISK_CTF_EXCHANGE"]

        for contract_name in required_contracts:
            assert contract_name in contracts, f"Contract {contract_name} not found"
            assert contracts[contract_name], f"Contract {contract_name} has empty address"

        print(f"[PASS] test_contract_addresses_defined ({len(required_contracts)} contracts)")

    def test_contract_addresses_valid_format(self):
        """test_contract_addresses_valid_format — addresses are valid hex"""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))
        from config.polymarket_contracts import POLYMARKET_CONTRACTS

        contracts = POLYMARKET_CONTRACTS["contracts"]
        # Ethereum address pattern: 0x followed by 40 hex characters
        address_pattern = re.compile(r'^0x[a-fA-F0-9]{40}$')

        for name, address in contracts.items():
            assert address_pattern.match(address), \
                f"Contract {name} has invalid address format: {address}"

        print(f"[PASS] test_contract_addresses_valid_format ({len(contracts)} addresses validated)")

    def test_network_configuration(self):
        """test_network_configuration — Polygon network is configured"""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))
        from config.polymarket_contracts import POLYMARKET_CONTRACTS

        assert POLYMARKET_CONTRACTS["network"] == "Polygon", "Network should be Polygon"
        assert POLYMARKET_CONTRACTS["chain_id"] == 137, "Chain ID should be 137"

        print("[PASS] test_network_configuration")


class TestWeb3StubFunctions:
    """Tests for Web3 stub functions"""

    def test_get_usdc_balance_stub(self):
        """test_get_usdc_balance_stub — stub returns 0"""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))
        from config.polymarket_contracts import get_usdc_balance

        balance = get_usdc_balance("0x1234567890123456789012345678901234567890")
        assert balance == 0.0, "Stub should return 0.0"

        print("[PASS] test_get_usdc_balance_stub")

    def test_get_ctf_condition_stub(self):
        """test_get_ctf_condition_stub — stub returns empty condition"""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))
        from config.polymarket_contracts import get_ctf_condition

        condition = get_ctf_condition("0x1234567890123456789012345678901234567890123456789012345678901234")
        assert "oracle" in condition, "Should have 'oracle' field"
        assert "questionId" in condition, "Should have 'questionId' field"
        assert "outcomeSlotCount" in condition, "Should have 'outcomeSlotCount' field"

        print("[PASS] test_get_ctf_condition_stub")

    def test_buy_outcome_tokens_stub(self):
        """test_buy_outcome_tokens_stub — stub returns failure response"""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))
        from config.polymarket_contracts import buy_outcome_tokens

        result = buy_outcome_tokens(
            wallet_address="0x1234567890123456789012345678901234567890",
            condition_id="0x1234",
            outcome_index=0,
            amount=100.0
        )

        assert "success" in result, "Should have 'success' field"
        assert result["success"] == False, "Stub should return success=False"
        assert "message" in result, "Should have 'message' field"
        assert "not yet implemented" in result["message"].lower(), "Message should indicate not implemented"

        print("[PASS] test_buy_outcome_tokens_stub")

    def test_sell_outcome_tokens_stub(self):
        """test_sell_outcome_tokens_stub — stub returns failure response"""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))
        from config.polymarket_contracts import sell_outcome_tokens

        result = sell_outcome_tokens(
            wallet_address="0x1234567890123456789012345678901234567890",
            condition_id="0x1234",
            outcome_index=0,
            amount=100.0
        )

        assert "success" in result, "Should have 'success' field"
        assert result["success"] == False, "Stub should return success=False"

        print("[PASS] test_sell_outcome_tokens_stub")


class TestABIConfiguration:
    """Tests for ABI configuration"""

    def test_usdc_abi_defined(self):
        """test_usdc_abi_defined — USDC ABI is defined"""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))
        from config.polymarket_contracts import USDC_ABI

        assert isinstance(USDC_ABI, list), "USDC_ABI should be a list"
        assert len(USDC_ABI) > 0, "USDC_ABI should not be empty"

        # Check for balanceOf function
        balance_of_found = False
        for item in USDC_ABI:
            if item.get("name") == "balanceOf":
                balance_of_found = True
                break

        assert balance_of_found, "USDC_ABI should contain balanceOf function"

        print(f"[PASS] test_usdc_abi_defined ({len(USDC_ABI)} functions)")

    def test_ctf_abi_defined(self):
        """test_ctf_abi_defined — CTF ABI is defined"""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))
        from config.polymarket_contracts import CTF_ABI

        assert isinstance(CTF_ABI, list), "CTF_ABI should be a list"
        assert len(CTF_ABI) > 0, "CTF_ABI should not be empty"

        print(f"[PASS] test_ctf_abi_defined ({len(CTF_ABI)} functions)")

    def test_ctf_exchange_abi_defined(self):
        """test_ctf_exchange_abi_defined — CTF Exchange ABI is defined"""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))
        from config.polymarket_contracts import CTF_EXCHANGE_ABI

        assert isinstance(CTF_EXCHANGE_ABI, list), "CTF_EXCHANGE_ABI should be a list"
        assert len(CTF_EXCHANGE_ABI) > 0, "CTF_EXCHANGE_ABI should not be empty"

        # Check for buy function
        buy_found = False
        for item in CTF_EXCHANGE_ABI:
            if item.get("name") == "buy":
                buy_found = True
                break

        assert buy_found, "CTF_EXCHANGE_ABI should contain buy function"

        print(f"[PASS] test_ctf_exchange_abi_defined ({len(CTF_EXCHANGE_ABI)} functions)")


class TestFrontendWeb3Config:
    """Tests for frontend Web3 configuration (TypeScript)"""

    def test_frontend_config_syntax(self):
        """test_frontend_config_syntax — TypeScript config has valid syntax"""
        config_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'web3Config.ts')
        
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Basic checks
        assert 'export const POLYMARKET_CONTRACTS' in content, "Should export POLYMARKET_CONTRACTS"
        assert 'chainId: 137' in content, "Should have chainId: 137"
        assert 'USDC_E:' in content, "Should have USDC_E contract"
        assert 'CTF:' in content, "Should have CTF contract"
        assert 'CTF_EXCHANGE:' in content, "Should have CTF_EXCHANGE contract"

        print("[PASS] test_frontend_config_syntax")

    def test_frontend_stub_functions(self):
        """test_frontend_stub_functions — frontend stub functions exist"""
        config_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'web3Config.ts')
        
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()

        required_functions = [
            'getUsdcBalance',
            'getCtfCondition',
            'buyOutcomeTokens',
            'sellOutcomeTokens',
            'connectWallet'
        ]

        for func in required_functions:
            assert f'export async function {func}' in content or f'export function {func}' in content, \
                f"Function {func} not found"

        print(f"[PASS] test_frontend_stub_functions ({len(required_functions)} functions)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
