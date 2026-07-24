#!/usr/local/bin/php
<?php

require_once('legacy_bindings.inc');

use OPNsense\Auth\User;
use OPNsense\Auth\Group;
use OPNsense\Core\Config;

const USERNAME = 'homeassistant_muse';
const PRIVILEGE = 'page-muse-readonly';

Config::getInstance()->lock();
$model = new User();
$user = $model->getUserByName(USERNAME);
$created = false;

if ($user === null) {
    $user = $model->user->Add();
    $user->name = USERNAME;
    $user->scope = 'automation';
    $user->descr = 'Home Assistant read-only gateway telemetry';
    $password = random_bytes(50);
    while (($position = strpos($password, "\0")) !== false) {
        $password[$position] = random_bytes(1);
    }
    $user->password = $model->generatePasswordHash($password);
    $created = true;
}

// Never inherit a broader role: this exact privilege is the whole authority.
$user->priv = PRIVILEGE;
$groups = new Group();
foreach ($groups->group->iterateItems() as $group) {
    $members = $group->member->getValues();
    $position = array_search((string)$user->uid, $members, true);
    if ($position !== false) {
        unset($members[$position]);
        $group->member = implode(',', $members);
    }
}
$messages = $model->performValidation();
$userMessages = [];
foreach ($messages as $message) {
    if (strpos($message->getField(), $user->__reference) !== false) {
        $userMessages[] = $message->getMessage();
    }
}
if (count($userMessages) > 0) {
    Config::getInstance()->unlock();
    fwrite(STDERR, "OPNsense user validation failed: " . implode('; ', $userMessages) . "\n");
    exit(1);
}

$keys = $user->apikeys->all();
$credential = null;
if (count($keys) === 0) {
    $credential = $user->apikeys->add();
}

if (!$model->serializeToConfig(false, true)) {
    Config::getInstance()->unlock();
    fwrite(STDERR, "Unable to serialize OPNsense user configuration\n");
    exit(1);
}
$groups->serializeToConfig(false, true);
Config::getInstance()->save("Provision Muse read-only gateway telemetry");
configdp_run('auth user changed', [USERNAME]);

$result = [
    'status' => $credential === null ? 'already_configured' : 'configured',
    'created' => $created,
    'username' => USERNAME,
    'privilege' => PRIVILEGE,
];
if ($credential !== null) {
    $result = array_merge($result, $credential);
}
echo json_encode($result, JSON_UNESCAPED_SLASHES), "\n";
