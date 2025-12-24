import { useState, useEffect, useRef } from 'react';
import { Plus, Trash2 } from 'lucide-react';

export interface LineItem {
  description: string;
  qty: number;
  unitPrice: number;
  taxRate: number; // Stored as number: 0, 8, or 10
}

interface LineItemsTableProps {
  items: LineItem[];
  onItemsChange: (items: LineItem[]) => void;
}

const ALLOWED_TAX_RATES = [0, 8, 10] as const;

// Internal state for raw string values during editing
interface RawItem {
  description: string;
  qty: string; // Raw string value
  unitPrice: string; // Raw string value
  taxRate: number;
}

export function LineItemsTable({ items, onItemsChange }: LineItemsTableProps) {
  // Store raw string values for qty and unitPrice to allow temporary empty state
  const [rawItems, setRawItems] = useState<RawItem[]>(() =>
    items.map(item => ({
      description: item.description,
      qty: item.qty.toString(),
      unitPrice: item.unitPrice.toString(),
      taxRate: item.taxRate,
    }))
  );

  // Track the last items we processed to detect external changes
  const lastItemsRef = useRef<LineItem[]>(items);

  // Sync rawItems when items prop changes externally (not from our own updates)
  useEffect(() => {
    // Check if this is an external change (items changed but not from our handleItemChange)
    const isExternalChange = 
      items.length !== lastItemsRef.current.length ||
      items.some((item, idx) => {
        if (idx >= lastItemsRef.current.length) return true;
        const last = lastItemsRef.current[idx];
        return item.description !== last.description ||
               Math.abs(item.qty - last.qty) > 0.01 ||
               Math.abs(item.unitPrice - last.unitPrice) > 0.01 ||
               item.taxRate !== last.taxRate;
      });

    if (isExternalChange) {
      // When syncing externally, convert items to rawItems
      // Preserve empty strings only if the current rawItems has them and item value is 0
      setRawItems(prevRawItems => {
        return items.map((item, idx) => {
          const currentRaw = prevRawItems[idx];
          // If we have a current raw item with empty strings and item value is 0, preserve empty
          if (currentRaw && idx < prevRawItems.length) {
            return {
              description: item.description,
              qty: (item.qty === 0 && currentRaw.qty.trim() === '') ? '' : item.qty.toString(),
              unitPrice: (item.unitPrice === 0 && currentRaw.unitPrice.trim() === '') ? '' : item.unitPrice.toString(),
              taxRate: item.taxRate,
            };
          }
          // Otherwise, convert normally
          return {
            description: item.description,
            qty: item.qty.toString(),
            unitPrice: item.unitPrice.toString(),
            taxRate: item.taxRate,
          };
        });
      });
      lastItemsRef.current = items;
    }
  }, [items]);

  const handleItemChange = (index: number, field: keyof RawItem, value: string | number) => {
    const updated = [...rawItems];
    updated[index] = { ...updated[index], [field]: value };
    setRawItems(updated);

    // Always update parent for calculation purposes, but preserve raw strings in rawItems
    // This allows totals to update in real-time while keeping empty strings during typing
    const lineItems: LineItem[] = updated.map(raw => ({
      description: raw.description,
      qty: raw.qty.trim() === '' ? 0 : parseFloat(raw.qty) || 0,
      unitPrice: raw.unitPrice.trim() === '' ? 0 : parseFloat(raw.unitPrice) || 0,
      taxRate: raw.taxRate,
    }));
    
    // Update ref to track this as our own change
    lastItemsRef.current = lineItems;
    onItemsChange(lineItems);
  };

  // Handle blur for qty and unitPrice - normalize empty strings to "0" for consistency
  const handleNumericBlur = (index: number, field: 'qty' | 'unitPrice') => {
    const rawValue = rawItems[index][field];
    const parsed = rawValue.trim() === '' ? 0 : parseFloat(rawValue) || 0;
    
    // If empty, keep as empty string; if parsed, use the parsed value as string
    // This preserves the user's intent: empty stays empty, numbers stay as numbers
    const updated = [...rawItems];
    if (rawValue.trim() === '') {
      // Keep empty string - don't convert to "0"
      updated[index] = { ...updated[index], [field]: '' };
    } else {
      // Use parsed value to normalize (e.g., "1.0" -> "1")
      updated[index] = { ...updated[index], [field]: parsed.toString() };
    }
    setRawItems(updated);

    // Update parent with parsed values
    const lineItems: LineItem[] = updated.map(raw => ({
      description: raw.description,
      qty: raw.qty.trim() === '' ? 0 : parseFloat(raw.qty) || 0,
      unitPrice: raw.unitPrice.trim() === '' ? 0 : parseFloat(raw.unitPrice) || 0,
      taxRate: raw.taxRate,
    }));
    
    lastItemsRef.current = lineItems;
    onItemsChange(lineItems);
  };

  const handleAddRow = () => {
    const newItem: LineItem = { description: '', qty: 1, unitPrice: 0, taxRate: 10 };
    const updatedItems = [...items, newItem];
    lastItemsRef.current = updatedItems;
    onItemsChange(updatedItems);
    // Also update rawItems to keep in sync
    setRawItems([...rawItems, {
      description: '',
      qty: '1',
      unitPrice: '0',
      taxRate: 10,
    }]);
  };

  const handleRemoveRow = (index: number) => {
    if (items.length > 1) {
      const updated = items.filter((_, i) => i !== index);
      lastItemsRef.current = updated;
      onItemsChange(updated);
      // Also update rawItems to keep in sync
      const updatedRaw = rawItems.filter((_, i) => i !== index);
      setRawItems(updatedRaw);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <label className="block text-sm text-gray-400">Line Items</label>
        <button
          type="button"
          onClick={handleAddRow}
          className="flex items-center gap-2 px-3 py-1.5 text-sm text-primary hover:text-primary-hover transition-colors"
        >
          <Plus size={16} />
          Add Row
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-dark-border">
              <th className="text-left py-2 px-3 text-xs font-medium text-gray-400">Description</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-gray-400">Qty</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-gray-400">Unit Price</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-gray-400">Tax Rate</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-gray-400">Amount</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-gray-400"></th>
            </tr>
          </thead>
          <tbody>
            {rawItems.map((rawItem, index) => {
              // Calculate amount using parsed values (use 0 if empty)
              const qty = rawItem.qty.trim() === '' ? 0 : parseFloat(rawItem.qty) || 0;
              const unitPrice = rawItem.unitPrice.trim() === '' ? 0 : parseFloat(rawItem.unitPrice) || 0;
              const amount = qty * unitPrice;
              
              // Use stable key based on index to ensure inputs remain mounted
              return (
                <tr key={`line-item-${index}`} className="border-b border-dark-border">
                  <td className="py-2 px-3">
                    <input
                      type="text"
                      value={rawItem.description}
                      onChange={(e) => handleItemChange(index, 'description', e.target.value)}
                      className="w-full bg-dark-bg border border-dark-border rounded px-2 py-1 text-sm text-white focus:outline-none focus:border-primary"
                    />
                  </td>
                  <td className="py-2 px-3">
                    <input
                      type="number"
                      min="0.01"
                      step="0.01"
                      value={rawItem.qty}
                      onChange={(e) => handleItemChange(index, 'qty', e.target.value)}
                      onBlur={() => handleNumericBlur(index, 'qty')}
                      className="w-full bg-dark-bg border border-dark-border rounded px-2 py-1 text-sm text-white focus:outline-none focus:border-primary"
                    />
                  </td>
                  <td className="py-2 px-3">
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={rawItem.unitPrice}
                      onChange={(e) => handleItemChange(index, 'unitPrice', e.target.value)}
                      onBlur={() => handleNumericBlur(index, 'unitPrice')}
                      className="w-full bg-dark-bg border border-dark-border rounded px-2 py-1 text-sm text-white focus:outline-none focus:border-primary"
                    />
                  </td>
                  <td className="py-2 px-3">
                    <select
                      value={rawItem.taxRate}
                      onChange={(e) => handleItemChange(index, 'taxRate', parseInt(e.target.value, 10))}
                      className="w-full bg-dark-bg border border-dark-border rounded px-2 py-1 text-sm text-white focus:outline-none focus:border-primary"
                    >
                      {ALLOWED_TAX_RATES.map((rate) => (
                        <option key={rate} value={rate}>
                          {rate}%
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="py-2 px-3 text-sm text-gray-300">
                    ¥{amount.toFixed(2)}
                  </td>
                  <td className="py-2 px-3">
                    {rawItems.length > 1 && (
                      <button
                        type="button"
                        onClick={() => handleRemoveRow(index)}
                        className="text-error hover:text-error-hover transition-colors"
                      >
                        <Trash2 size={16} />
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
