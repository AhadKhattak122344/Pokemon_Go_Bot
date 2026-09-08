-- Android Fleet Database Schema
-- PostgreSQL database for instance state management

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Instances table: tracks all VM instances
CREATE TABLE instances (
    id SERIAL PRIMARY KEY,
    vm_id INTEGER NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    machine_type VARCHAR(50),
    identity JSONB NOT NULL,
    config JSONB,
    metadata JSONB,
    ip_address INET,
    adb_port INTEGER DEFAULT 5555,
    last_heartbeat TIMESTAMP WITH TIME ZONE,
    CONSTRAINT chk_status CHECK (status IN ('pending', 'running', 'stopped', 'failed', 'destroyed'))
);

-- Identity profiles: detailed device identity information
CREATE TABLE identity_profiles (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER REFERENCES instances(id) ON DELETE CASCADE,
    android_id VARCHAR(32) NOT NULL,
    imei VARCHAR(15) NOT NULL,
    mac_address VARCHAR(17) NOT NULL,
    serial VARCHAR(32) NOT NULL,
    model VARCHAR(50) NOT NULL,
    manufacturer VARCHAR(50) NOT NULL,
    device VARCHAR(50),
    name VARCHAR(50),
    fingerprint TEXT NOT NULL,
    description TEXT,
    sdk VARCHAR(10),
    release VARCHAR(10),
    assigned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(android_id),
    UNIQUE(imei),
    UNIQUE(mac_address)
);

-- Task history: track all operations performed on instances
CREATE TABLE task_history (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER REFERENCES instances(id) ON DELETE SET NULL,
    task_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    result JSONB,
    error TEXT,
    retry_count INTEGER DEFAULT 0,
    CONSTRAINT chk_task_status CHECK (status IN ('pending', 'running', 'completed', 'failed', 'retrying'))
);

-- Account vault: encrypted account credentials per instance
CREATE TABLE account_vault (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER REFERENCES instances(id) ON DELETE CASCADE,
    account_id VARCHAR(100) NOT NULL,
    account_type VARCHAR(50) NOT NULL,
    encrypted_data BYTEA NOT NULL,
    encryption_key_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB,
    UNIQUE(instance_id, account_id)
);

-- Application inventory: track installed apps per instance
CREATE TABLE app_inventory (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER REFERENCES instances(id) ON DELETE CASCADE,
    package_name VARCHAR(255) NOT NULL,
    version_code INTEGER,
    version_name VARCHAR(50),
    installed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'active',
    UNIQUE(instance_id, package_name)
);

-- Performance metrics: historical performance data
CREATE TABLE performance_metrics (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER REFERENCES instances(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    cpu_usage NUMERIC(5,2),
    memory_usage NUMERIC(5,2),
    memory_available BIGINT,
    disk_usage NUMERIC(5,2),
    network_rx BIGINT,
    network_tx BIGINT,
    app_launch_time_ms INTEGER,
    metadata JSONB
);

-- Node resources: track Proxmox node capacity
CREATE TABLE node_resources (
    id SERIAL PRIMARY KEY,
    node_name VARCHAR(100) NOT NULL UNIQUE,
    total_cpu_cores INTEGER NOT NULL,
    total_ram_gb INTEGER NOT NULL,
    total_storage_gb INTEGER NOT NULL,
    available_cpu_cores INTEGER,
    available_ram_gb INTEGER,
    available_storage_gb INTEGER,
    instance_count INTEGER DEFAULT 0,
    last_updated TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Notifications: event log for ntfy and other notification systems
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    instance_id INTEGER REFERENCES instances(id) ON DELETE SET NULL,
    title VARCHAR(200),
    message TEXT NOT NULL,
    priority INTEGER DEFAULT 3,
    sent_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    delivered BOOLEAN DEFAULT FALSE,
    response JSONB
);

-- Indexes for common queries
CREATE INDEX idx_instances_status ON instances(status);
CREATE INDEX idx_instances_vm_id ON instances(vm_id);
CREATE INDEX idx_instances_name ON instances(name);
CREATE INDEX idx_tasks_instance ON task_history(instance_id);
CREATE INDEX idx_tasks_status ON task_history(status);
CREATE INDEX idx_tasks_started ON task_history(started_at);
CREATE INDEX idx_accounts_instance ON account_vault(instance_id);
CREATE INDEX idx_apps_instance ON app_inventory(instance_id);
CREATE INDEX idx_metrics_instance ON performance_metrics(instance_id);
CREATE INDEX idx_metrics_timestamp ON performance_metrics(timestamp);
CREATE INDEX idx_identity_android_id ON identity_profiles(android_id);
CREATE INDEX idx_identity_imei ON identity_profiles(imei);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for instances table
CREATE TRIGGER update_instances_updated_at
    BEFORE UPDATE ON instances
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- View for active instances with identity
CREATE VIEW active_instances_view AS
SELECT 
    i.id,
    i.vm_id,
    i.name,
    i.status,
    i.ip_address,
    i.adb_port,
    ip.model,
    ip.manufacturer,
    ip.android_id,
    ip.imei,
    i.created_at,
    i.last_heartbeat
FROM instances i
LEFT JOIN identity_profiles ip ON i.id = ip.instance_id
WHERE i.status IN ('running', 'pending');

-- View for fleet statistics
CREATE VIEW fleet_statistics_view AS
SELECT 
    COUNT(*) as total_instances,
    COUNT(CASE WHEN status = 'running' THEN 1 END) as running_count,
    COUNT(CASE WHEN status = 'stopped' THEN 1 END) as stopped_count,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_count,
    AVG(CASE WHEN status = 'running' THEN EXTRACT(EPOCH FROM (NOW() - created_at)) END) as avg_uptime_seconds
FROM instances;

-- Insert default node (update with actual values)
INSERT INTO node_resources (node_name, total_cpu_cores, total_ram_gb, total_storage_gb)
VALUES ('proxmox', 64, 256, 4000)
ON CONFLICT (node_name) DO NOTHING;
