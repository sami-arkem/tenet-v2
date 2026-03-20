'use client';

import { useEffect, useState } from 'react';
import { Card, CardSection } from '@/components/ui/Card';
import { Badge, type BadgeVariant } from '@/components/ui/Badge';
import { Globe, BookOpen } from 'lucide-react';
import { request } from '@/lib/api';

interface PackSummary {
  pack_id: string;
  jurisdiction: string;
  version: string;
  control_count: number;
  domains: string[];
}

interface PackDetail {
  metadata: {
    pack_id: string;
    jurisdiction: string;
    country_codes: string[];
    regulators: string[];
    domains: string[];
    version: string;
    effective_date: string | null;
    priority: number;
    applicability_notes: string;
  };
  controls: ControlDetail[];
}

interface ControlDetail {
  control_id: string;
  control_name: string;
  severity: string;
  domain: string;
  jurisdiction: string;
}

export default function JurisdictionsPage() {
  const [packs, setPacks] = useState<PackSummary[]>([]);
  const [selectedJurisdiction, setSelectedJurisdiction] = useState<string>('US');
  const [selectedDomain, setSelectedDomain] = useState<string>('all');
  const [pack, setPack] = useState<PackDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load list of packs
  useEffect(() => {
    const loadPacks = async () => {
      try {
        const data = await request<PackSummary[]>('/v1/jurisdiction-packs');
        setPacks(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load packs');
      }
    };
    loadPacks();
  }, []);

  // Load pack details when jurisdiction changes
  useEffect(() => {
    const loadPack = async () => {
      if (!selectedJurisdiction) return;
      setLoading(true);
      try {
        const data = await request<PackDetail>(`/v1/jurisdiction-packs/${selectedJurisdiction}`);
        setPack(data);
        setSelectedDomain('all');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load pack');
      } finally {
        setLoading(false);
      }
    };
    loadPack();
  }, [selectedJurisdiction]);

  const filteredControls = pack?.controls.filter(c =>
    selectedDomain === 'all' || c.domain === selectedDomain
  ) || [];

  const domains = Array.from(new Set(pack?.controls.map(c => c.domain) || []));

  const getSeverityBadgeVariant = (severity: string): BadgeVariant => {
    switch (severity) {
      case 'CRITICAL':
        return 'critical';
      case 'HIGH':
        return 'high';
      case 'MEDIUM':
        return 'medium';
      default:
        return 'low';
    }
  };

  return (
    <div className="space-y-6 py-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
          <Globe className="h-8 w-8" />
          Jurisdiction Compliance Packs
        </h1>
        <p className="text-gray-600 mt-2">
          Global regulatory frameworks with world-class control coverage and evidence requirements.
        </p>
      </div>

      {error && (
        <Card className="border border-red-200 bg-red-50">
          <div className="text-red-800">{error}</div>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <div>
            <h2 className="text-lg font-semibold mb-2">Select Jurisdiction</h2>
            <p className="text-sm text-gray-600 mb-4">Choose a jurisdiction pack to explore</p>
          </div>
          <select
            value={selectedJurisdiction}
            onChange={(e) => setSelectedJurisdiction(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {packs.map(p => (
              <option key={p.pack_id} value={p.jurisdiction}>
                {p.jurisdiction} ({p.control_count} controls)
              </option>
            ))}
          </select>
        </Card>

        {pack && (
          <Card>
            <div>
              <h2 className="text-lg font-semibold">{pack.metadata.jurisdiction} Pack</h2>
              <p className="text-sm text-gray-600 mb-4">
                Version {pack.metadata.version} • {pack.controls.length} controls
              </p>
            </div>
            <CardSection>
              <div>
                <p className="text-sm font-medium mb-2">Regulators</p>
                <div className="flex flex-wrap gap-1">
                  {pack.metadata.regulators.slice(0, 3).map(r => (
                    <Badge key={r} variant="default" label={r} className="text-xs" />
                  ))}
                  {pack.metadata.regulators.length > 3 && (
                    <Badge variant="default" label={`+${pack.metadata.regulators.length - 3}`} className="text-xs" />
                  )}
                </div>
              </div>
              {pack.metadata.effective_date && (
                <div className="mt-3">
                  <p className="text-sm font-medium mb-1">Effective Date</p>
                  <p className="text-sm text-gray-600">{pack.metadata.effective_date}</p>
                </div>
              )}
            </CardSection>
          </Card>
        )}
      </div>

      {pack && (
        <>
          <Card>
            <h2 className="text-lg font-semibold mb-4">Filter by Domain</h2>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setSelectedDomain('all')}
                className={`px-3 py-1 rounded-md text-sm font-medium transition ${
                  selectedDomain === 'all'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                All Domains ({pack.controls.length})
              </button>
              {Array.from(domains).map(domain => {
                const count = pack.controls.filter(c => c.domain === domain).length;
                return (
                  <button
                    key={domain}
                    onClick={() => setSelectedDomain(domain)}
                    className={`px-3 py-1 rounded-md text-sm font-medium transition ${
                      selectedDomain === domain
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                    }`}
                  >
                    {domain} ({count})
                  </button>
                );
              })}
            </div>
          </Card>

          <div className="space-y-3">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <BookOpen className="h-5 w-5" />
              Controls
            </h2>

            {loading ? (
              <Card>
                <div>Loading...</div>
              </Card>
            ) : filteredControls.length === 0 ? (
              <Card>
                <div className="text-center text-gray-600">
                  No controls found for this domain.
                </div>
              </Card>
            ) : (
              <div className="space-y-3">
                {filteredControls.map(control => (
                  <Card key={control.control_id} className="hover:shadow-md transition">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 space-y-1">
                        <p className="font-mono text-sm font-bold text-gray-600">{control.control_id}</p>
                        <p className="font-medium">{control.control_name}</p>
                        <div className="flex gap-2 mt-2">
                          <Badge variant={getSeverityBadgeVariant(control.severity)} label={control.severity} />
                          <Badge variant="default" label={control.domain} />
                        </div>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
