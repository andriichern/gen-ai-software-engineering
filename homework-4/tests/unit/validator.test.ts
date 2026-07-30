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
});
