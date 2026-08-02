import { validateCreateOrder, validateUpdatePayment, validateStatusUpdate } from '@/lib/validator';
import { OrderStatus } from '@/lib/types';

describe('Validator', () => {
  describe('validateCreateOrder', () => {
    it('should accept valid order data', () => {
      const result = validateCreateOrder({
        orderedItems: ['item-1', 'item-2'],
        customerId: 'cust-123',
        deliveryAddress: '123 Main St',
      });

      expect(result.valid).toBe(true);
    });

    // BUG-1: orderedItems validation missing
    it('should reject orderedItems that is an empty array', () => {
      const result = validateCreateOrder({
        orderedItems: [],
        customerId: 'cust-123',
        deliveryAddress: '123 Main St',
      });

      expect(result.valid).toBe(false);
      expect(result.errors?.orderedItems).toBeDefined();
    });

    it('should reject orderedItems that is not an array', () => {
      const result = validateCreateOrder({
        orderedItems: 'item-1',
        customerId: 'cust-123',
        deliveryAddress: '123 Main St',
      });

      expect(result.valid).toBe(false);
      expect(result.errors?.orderedItems).toBeDefined();
    });

    it('should reject orderedItems with non-string elements', () => {
      const result = validateCreateOrder({
        orderedItems: ['item-1', 123],
        customerId: 'cust-123',
        deliveryAddress: '123 Main St',
      });

      expect(result.valid).toBe(false);
      expect(result.errors?.orderedItems).toBeDefined();
    });

    // BUG-2: deliveryAddress validation missing
    it('should reject empty deliveryAddress', () => {
      const result = validateCreateOrder({
        orderedItems: ['item-1'],
        customerId: 'cust-123',
        deliveryAddress: '',
      });

      expect(result.valid).toBe(false);
      expect(result.errors?.deliveryAddress).toBeDefined();
    });

    it('should reject null deliveryAddress', () => {
      const result = validateCreateOrder({
        orderedItems: ['item-1'],
        customerId: 'cust-123',
        deliveryAddress: null,
      });

      expect(result.valid).toBe(false);
      expect(result.errors?.deliveryAddress).toBeDefined();
    });

    it('should reject missing customerId', () => {
      const result = validateCreateOrder({
        orderedItems: ['item-1'],
        deliveryAddress: '123 Main St',
      });

      expect(result.valid).toBe(false);
      expect(result.errors?.customerId).toBeDefined();
    });
  });

  describe('validateUpdatePayment', () => {
    it('should accept valid payment data', () => {
      const result = validateUpdatePayment({
        paymentId: 'pay-123',
      });

      expect(result.valid).toBe(true);
    });

    it('should reject empty paymentId', () => {
      const result = validateUpdatePayment({
        paymentId: '',
      });

      expect(result.valid).toBe(false);
      expect(result.errors?.paymentId).toBeDefined();
    });

    it('should reject non-string paymentId', () => {
      const result = validateUpdatePayment({
        paymentId: 12345,
      });

      expect(result.valid).toBe(false);
      expect(result.errors?.paymentId).toBeDefined();
    });
  });

  describe('validateStatusUpdate', () => {
    it('should accept valid status', () => {
      const result = validateStatusUpdate(OrderStatus.Processing);
      expect(result.valid).toBe(true);
    });

    it('should reject invalid status', () => {
      const result = validateStatusUpdate('InvalidStatus');
      expect(result.valid).toBe(false);
      expect(result.error).toBeDefined();
    });

    it('should reject non-string status', () => {
      const result = validateStatusUpdate(123);
      expect(result.valid).toBe(false);
      expect(result.error).toBeDefined();
    });
  });

  describe('validateCreateOrder - Enhanced Coverage (FIRST Principles)', () => {
    describe('Happy Path', () => {
      it('should validate order with single item', () => {
        const result = validateCreateOrder({
          orderedItems: ['single-item'],
          customerId: 'cust-001',
          deliveryAddress: '1 Park Lane',
        });
        expect(result.valid).toBe(true);
      });

      it('should validate order with multiple items', () => {
        const result = validateCreateOrder({
          orderedItems: ['item-a', 'item-b', 'item-c', 'item-d'],
          customerId: 'customer-xyz',
          deliveryAddress: 'Apartment 5, Building C',
        });
        expect(result.valid).toBe(true);
      });

      it('should accept alphanumeric customerId', () => {
        const result = validateCreateOrder({
          orderedItems: ['item'],
          customerId: 'CUST-2024-001',
          deliveryAddress: '123 Main St',
        });
        expect(result.valid).toBe(true);
      });

      it('should accept addresses with special characters', () => {
        const result = validateCreateOrder({
          orderedItems: ['item'],
          customerId: 'cust-123',
          deliveryAddress: '123 Oak Dr, Suite #200, New York, NY 10001',
        });
        expect(result.valid).toBe(true);
      });
    });

    describe('orderedItems - Boundary Cases', () => {
      it('should reject orderedItems with undefined', () => {
        const result = validateCreateOrder({
          customerId: 'cust-123',
          deliveryAddress: '123 Main St',
        });
        expect(result.valid).toBe(false);
        expect(result.errors?.orderedItems).toBe('orderedItems is required');
      });

      it('should reject orderedItems with null', () => {
        const result = validateCreateOrder({
          orderedItems: null,
          customerId: 'cust-123',
          deliveryAddress: '123 Main St',
        });
        expect(result.valid).toBe(false);
        expect(result.errors?.orderedItems).toBe('orderedItems must be an array');
      });

      it('should reject orderedItems as object', () => {
        const result = validateCreateOrder({
          orderedItems: { item1: 'value1' },
          customerId: 'cust-123',
          deliveryAddress: '123 Main St',
        });
        expect(result.valid).toBe(false);
        expect(result.errors?.orderedItems).toBe('orderedItems must be an array');
      });

      it('should reject orderedItems with mixed types (string and number)', () => {
        const result = validateCreateOrder({
          orderedItems: ['item1', 2, 'item3'],
          customerId: 'cust-123',
          deliveryAddress: '123 Main St',
        });
        expect(result.valid).toBe(false);
        expect(result.errors?.orderedItems).toBe('all orderedItems must be strings');
      });

      it('should reject orderedItems with boolean element', () => {
        const result = validateCreateOrder({
          orderedItems: ['item1', true],
          customerId: 'cust-123',
          deliveryAddress: '123 Main St',
        });
        expect(result.valid).toBe(false);
        expect(result.errors?.orderedItems).toBe('all orderedItems must be strings');
      });

      it('should reject orderedItems with null element', () => {
        const result = validateCreateOrder({
          orderedItems: ['item1', null, 'item2'],
          customerId: 'cust-123',
          deliveryAddress: '123 Main St',
        });
        expect(result.valid).toBe(false);
        expect(result.errors?.orderedItems).toBe('all orderedItems must be strings');
      });

      it('should reject orderedItems with undefined element', () => {
        const result = validateCreateOrder({
          orderedItems: ['item1', undefined, 'item2'],
          customerId: 'cust-123',
          deliveryAddress: '123 Main St',
        });
        expect(result.valid).toBe(false);
        expect(result.errors?.orderedItems).toBe('all orderedItems must be strings');
      });

      it('should accept orderedItems with empty string element (type is correct)', () => {
        const result = validateCreateOrder({
          orderedItems: ['item1', '', 'item3'],
          customerId: 'cust-123',
          deliveryAddress: '123 Main St',
        });
        expect(result.valid).toBe(true);
      });

      it('should accept orderedItems with whitespace-only string element', () => {
        const result = validateCreateOrder({
          orderedItems: ['item1', '   ', 'item3'],
          customerId: 'cust-123',
          deliveryAddress: '123 Main St',
        });
        expect(result.valid).toBe(true);
      });

      it('should reject orderedItems with object element', () => {
        const result = validateCreateOrder({
          orderedItems: ['item1', { item: 'value' }],
          customerId: 'cust-123',
          deliveryAddress: '123 Main St',
        });
        expect(result.valid).toBe(false);
        expect(result.errors?.orderedItems).toBe('all orderedItems must be strings');
      });

      it('should reject orderedItems as primitive number', () => {
        const result = validateCreateOrder({
          orderedItems: 42,
          customerId: 'cust-123',
          deliveryAddress: '123 Main St',
        });
        expect(result.valid).toBe(false);
        expect(result.errors?.orderedItems).toBe('orderedItems must be an array');
      });

      it('should reject orderedItems as boolean', () => {
        const result = validateCreateOrder({
          orderedItems: false,
          customerId: 'cust-123',
          deliveryAddress: '123 Main St',
        });
        expect(result.valid).toBe(false);
        expect(result.errors?.orderedItems).toBe('orderedItems must be an array');
      });
    });

    describe('deliveryAddress - Boundary Cases', () => {
      it('should reject deliveryAddress with undefined', () => {
        const result = validateCreateOrder({
          orderedItems: ['item'],
          customerId: 'cust-123',
        });
        expect(result.valid).toBe(false);
        expect(result.errors?.deliveryAddress).toBe('deliveryAddress must be a string');
      });

      it('should reject deliveryAddress with null', () => {
        const result = validateCreateOrder({
          orderedItems: ['item'],
          customerId: 'cust-123',
          deliveryAddress: null,
        });
        expect(result.valid).toBe(false);
        expect(result.errors?.deliveryAddress).toBe('deliveryAddress must be a string');
      });

      it('should reject deliveryAddress as number', () => {
        const result = validateCreateOrder({
          orderedItems: ['item'],
          customerId: 'cust-123',
          deliveryAddress: 12345,
        });
        expect(result.valid).toBe(false);
        expect(result.errors?.deliveryAddress).toBe('deliveryAddress must be a string');
      });

      it('should reject deliveryAddress as object', () => {
        const result = validateCreateOrder({
          orderedItems: ['item'],
          customerId: 'cust-123',
          deliveryAddress: { street: '123 Main St' },
        });
        expect(result.valid).toBe(false);
        expect(result.errors?.deliveryAddress).toBe('deliveryAddress must be a string');
      });

      it('should reject deliveryAddress as array', () => {
        const result = validateCreateOrder({
          orderedItems: ['item'],
          customerId: 'cust-123',
          deliveryAddress: ['123 Main St'],
        });
        expect(result.valid).toBe(false);
        expect(result.errors?.deliveryAddress).toBe('deliveryAddress must be a string');
      });

      it('should reject deliveryAddress with whitespace-only string', () => {
        const result = validateCreateOrder({
          orderedItems: ['item'],
          customerId: 'cust-123',
          deliveryAddress: '     ',
        });
        expect(result.valid).toBe(false);
        expect(result.errors?.deliveryAddress).toBe('deliveryAddress must not be empty');
      });

      it('should reject deliveryAddress with tab and newline only', () => {
        const result = validateCreateOrder({
          orderedItems: ['item'],
          customerId: 'cust-123',
          deliveryAddress: '\t\n  ',
        });
        expect(result.valid).toBe(false);
        expect(result.errors?.deliveryAddress).toBe('deliveryAddress must not be empty');
      });

      it('should accept deliveryAddress with minimal content', () => {
        const result = validateCreateOrder({
          orderedItems: ['item'],
          customerId: 'cust-123',
          deliveryAddress: 'X',
        });
        expect(result.valid).toBe(true);
      });

      it('should accept deliveryAddress with leading/trailing spaces (trimmed)', () => {
        const result = validateCreateOrder({
          orderedItems: ['item'],
          customerId: 'cust-123',
          deliveryAddress: '  123 Main St  ',
        });
        expect(result.valid).toBe(true);
      });
    });

    describe('customerId - Boundary Cases', () => {
      it('should reject customerId with undefined', () => {
        const result = validateCreateOrder({
          orderedItems: ['item'],
          deliveryAddress: '123 Main St',
        });
        expect(result.valid).toBe(false);
        expect(result.errors?.customerId).toBeDefined();
      });

      it('should reject customerId with null', () => {
        const result = validateCreateOrder({
          orderedItems: ['item'],
          customerId: null,
          deliveryAddress: '123 Main St',
        });
        expect(result.valid).toBe(false);
        expect(result.errors?.customerId).toBeDefined();
      });

      it('should reject customerId with empty string', () => {
        const result = validateCreateOrder({
          orderedItems: ['item'],
          customerId: '',
          deliveryAddress: '123 Main St',
        });
        expect(result.valid).toBe(false);
        expect(result.errors?.customerId).toBeDefined();
      });

      it('should reject customerId with whitespace-only string', () => {
        const result = validateCreateOrder({
          orderedItems: ['item'],
          customerId: '    ',
          deliveryAddress: '123 Main St',
        });
        expect(result.valid).toBe(false);
        expect(result.errors?.customerId).toBeDefined();
      });

      it('should reject customerId as number', () => {
        const result = validateCreateOrder({
          orderedItems: ['item'],
          customerId: 12345,
          deliveryAddress: '123 Main St',
        });
        expect(result.valid).toBe(false);
        expect(result.errors?.customerId).toBeDefined();
      });
    });

    describe('Multiple Errors', () => {
      it('should report all validation errors simultaneously', () => {
        const result = validateCreateOrder({
          orderedItems: [],
          customerId: '',
          deliveryAddress: '',
        });
        expect(result.valid).toBe(false);
        expect(result.errors?.orderedItems).toBeDefined();
        expect(result.errors?.customerId).toBeDefined();
        expect(result.errors?.deliveryAddress).toBeDefined();
      });

      it('should report errors for invalid orderedItems and deliveryAddress', () => {
        const result = validateCreateOrder({
          orderedItems: 'not-an-array',
          customerId: 'cust-123',
          deliveryAddress: null,
        });
        expect(result.valid).toBe(false);
        expect(result.errors?.orderedItems).toBe('orderedItems must be an array');
        expect(result.errors?.deliveryAddress).toBe('deliveryAddress must be a string');
      });
    });
  });
});
