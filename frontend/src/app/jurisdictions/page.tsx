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
  const [selectedJurisdiction, setSelectedJurisdiction] = useState<string | null>(null);
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

      {/* Jurisdiction Packs Grid */}
      {!selectedJurisdiction && (
        <div>
          <h2 className="text-xl font-semibold mb-4">Available Jurisdiction Packs ({packs.length})</h2>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
            {packs.map(p => (
              <Card
                key={p.pack_id}
                className="cursor-pointer hover:shadow-lg transition-shadow"
                onClick={() => setSelectedJurisdiction(p.jurisdiction)}
              >
                <div className="space-y-3">
                  <div>
                    <h3 className="text-lg font-bold">{p.jurisdiction}</h3>
                    <p className="text-sm text-gray-600 mt-1">{p.pack_id}</p>
                  </div>
                  <div className="border-t pt-3">
                    <p className="text-sm">
                      <span className="font-medium text-lg">{p.control_count}</span>
                      <span className="text-gray-600 ml-1">controls</span>
                    </p>
                    <p className="text-xs text-gray-500 mt-1">{p.domains.length} domains covered</p>
                  </div>
                  <div className="text-xs text-blue-600 font-medium">View Details →</div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Selected Pack Details */}
      {selectedJurisdiction && pack && (
        <div>
          <button
            onClick={() => setSelectedJurisdiction(null)}
            className="mb-4 px-3 py-2 text-sm font-medium text-blue-600 hover:text-blue-700 hover:underline"
          >
            ← Back to All Packs
          </button>

          <div className="grid gap-4 md:grid-cols-3">
            <Card className="md:col-span-1">
              <div>
                <h2 className="text-lg font-semibold">{pack.metadata.jurisdiction} Pack</h2>
                <p className="text-sm text-gray-600 mb-4">
                  Version {pack.metadata.version}
                </p>
              </div>
              <CardSection>
                <div>
                  <p className="text-sm font-medium mb-2">Regulators</p>
                  <div className="space-y-1">
                    {pack.metadata.regulators.map(r => (
                      <p key={r} className="text-sm text-gray-700">{r}</p>
                    ))}
                  </div>
                </div>
                <div className="mt-4">
                  <p className="text-sm font-medium mb-2">Coverage</p>
                  <p className="text-sm text-gray-600">{pack.controls.length} controls</p>
                  <p className="text-sm text-gray-600">{pack.metadata.domains.length} domains</p>
                </div>
                {pack.metadata.effective_date && (
                  <div className="mt-4">
                    <p className="text-sm font-medium mb-1">Effective Date</p>
                    <p className="text-sm text-gray-600">{pack.metadata.effective_date}</p>
                  </div>
                )}
              </CardSection>
            </Card>

            <div className="md:col-span-2 space-y-4">
              {/* Domain Filter */}
              <Card>
                <h3 className="text-lg font-semibold mb-3">Filter by Domain</h3>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => setSelectedDomain('all')}
                    className={`px-3 py-1 rounded-md text-sm font-medium transition ${
                      selectedDomain === 'all'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                    }`}
                  >
                    All ({pack.controls.length})
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

              {/* Controls List */}
              <div className="space-y-3">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <BookOpen className="h-5 w-5" />
                  Controls
                </h3>

                {loading ? (
                  <Card><div>Loading controls...</div></Card>
                ) : filteredControls.length === 0 ? (
                  <Card><div className="text-center text-gray-600">No controls found for this domain.</div></Card>
                ) : (
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {filteredControls.map(control => (
                      <Card key={control.control_id} className="hover:shadow-md transition p-3">
                        <div className="space-y-1">
                          <p className="font-mono text-sm font-bold text-gray-600">{control.control_id}</p>
                          <p className="font-medium text-sm">{control.control_name}</p>
                          <div className="flex gap-2 mt-2">
                            <Badge variant={getSeverityBadgeVariant(control.severity)} label={control.severity} />
                            <Badge variant="default" label={control.domain} />
                          </div>
                        </div>
                      </Card>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
